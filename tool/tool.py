#!/usr/bin/env python

import contextlib
from functools import partial, reduce
from itertools import count, groupby
from operator import itemgetter, attrgetter, add
from sys import stderr, stdin, stdout
from dataclasses import dataclass, field
import sys
from typing import Iterable, List, Optional, Sequence, Tuple
from clingo.symbol import Symbol, SymbolType, Number
from clingo.control import Control
from clingo.solving import Model
from clingox.reify import reify_program
from clingo.ast import AST
from math import inf
import typer
from pathlib import Path
from transforms.util import parse_rules
from io import StringIO
from functools import wraps


SHOW_ANSWER_SET_OPTION = typer.Option(
    False, help="Output every atom as it appears in the answer set")
INCREMENTAL_OPTION = typer.Option(
    False, help="Use Clingo's incremental solver")
ACCEPT_TESTS_OPTION = typer.Option(
    False, help="Accept the current output of regression tests")

# Hide an option from Typer
# https://github.com/fastapi/typer/issues/506#issuecomment-2340622424
OUTPUT_FILE = typer.Option(parser=lambda _: _, hidden=True, expose_value=False, default=stdout)


def is_not_none(x): return x is not None


app = typer.Typer()


@dataclass
class Interpretation:
    # Using default_factory to avoid footgun where all Python class instances share same data when statically initialized
    # (mutation of one instance affects all)
    # But that is fine for immutable data like booleans
    h: "set[str]" = field(default_factory=set)
    t: "set[str]" = field(default_factory=set)

    @staticmethod
    def __set_repr(data: "set[str]") -> str:
        return f"{{ {', '.join(sorted(data))} }}"

    def padded_string(self, padding: "tuple[int, int]") -> str:
        "Prints this interpretation by adding whitespace padding inside"
        return (f"({self.__set_repr(self.h)},".ljust(padding[0]) + f" {self.__set_repr(self.t)})").ljust(padding[1])

    def __str__(self) -> str:
        return self.padded_string((0, 0))

    def compute_padding(self) -> "tuple[int, int]":
        """Computes a pair (x, y) where x is the number of characters before the second interpretation
        is printed, y is the total number of characters this interpretation occupies.
        To be used with padded_string with a (possibly larger) padding so that interpretations line up when printed"""

        string = str(self)
        return (
            len(string[:string.index("},")+1]),
            len(string),
        )


    def __add__(self, other: "Interpretation") -> "Interpretation":
        "Return the pairwise union of both interpretations"
        if not isinstance(other, Interpretation):
            return NotImplemented
        return Interpretation(self.h | other.h, self.t | other.t)

    def __lt__(self, other) -> bool:
        """Simple lexigraphical ordering intended only for ensuring printed output is deterministic"""
        if not isinstance(other, Interpretation):
            return NotImplemented
        key = lambda x: (self.__set_repr(self.h), self.__set_repr(self.t))
        return key(self) < key(other)



@dataclass
class SymbolSet:
    "Provides a deterministic ordering for atoms"
    data: set = field(default_factory=set)

    @dataclass
    class SymbolWrapper:
        value: Symbol

        def __lt__(self, other):
            """
            First, atoms are ordered by their step
            Atoms without a step come first
            Then, atoms are ordered by their model
            model(h) < model(t)
            then, by name
            unknown < holdsIn < fp ... etc
            finally, by string representation
            """
            if not isinstance(other, SymbolSet.SymbolWrapper):
                return NotImplemented
            numSelf = get_step_arg(self.value)
            numOther = get_step_arg(other.value)
            if numSelf is None and numOther is not None:
                return True
            if numOther is None and numSelf is not None:
                return False
            if (not (numSelf is numOther is None)) and step_lt_step(numSelf, numOther):
                return True

            models = ("h", "t")
            known = ("hold", "holdsIn", "strict_partial_prefp",
                     "strict_partial_postfp", "fp")

            def index(names, name): return names.index(
                name) if name in names else -inf

            def key(symbol: SymbolSet.SymbolWrapper):
                return (
                    index(models, get_model_arg(symbol.value)),
                    index(known, symbol.value.name),
                    symbol.value.name,
                    str(symbol),
                )

            return key(self) < key(other)

    def __iter__(self):
        return iter(sorted(self.data, key=SymbolSet.SymbolWrapper))

    def __add__(self, other: "SymbolSet"):
        return SymbolSet(self.data | other.data)

    def add(self, item: Symbol):
        self.data.add(item)


@dataclass
class Step:
    """
    Represents all atoms that share the same step value
    May be in a partial state (e.g. missing atoms in interpretation, or fixpoint is false)
    Use + to combine Steps of the same value to get the complete step
    This is done by StepSequence
    """
    id: tuple
    fixpoint_h: bool = False
    fixpoint_t: bool = False
    interpretation: Interpretation = field(default_factory=Interpretation)
    symbols: SymbolSet = field(default_factory=SymbolSet)

    def interpretation_padded_string(self, padding: "tuple[int, int]") -> str:
        return f"{self.interpretation.padded_string((padding[0], padding[1]))}     STEP {self.id}"

    def __str__(self):
        return self.interpretation_padded_string((0, 0))

    def compute_padding(self) -> "tuple[int, int]":
        return self.interpretation.compute_padding()

    def is_fixpoint(self) -> bool:
        return self.fixpoint_h and self.fixpoint_t

    @staticmethod
    def from_atom(symbol: Symbol) -> "Step | None":
        num = get_step_arg(symbol)
        if num is None:
            return None
        step = Step(num)
        step.symbols.add(symbol)
        model = get_model_arg(symbol)
        if symbol.name == "fp":
            step.fixpoint_h = model == "h"
            step.fixpoint_t = model == "t"
        elif symbol.name == "holdsIn":
            atom = symbol.arguments[0].name
            i = step.interpretation.h if model == "h" else step.interpretation.t
            i.add(atom)
        return step

    def __lt__(self, other: "Step") -> bool:
        if not isinstance(other, Step):
            return NotImplemented
        return step_lt_step(self.id, other.id)

    def __eq__(self, other: "Step") -> bool:
        return self.id == other.id

    def __add__(self, other: "Step") -> "Step":
        if not isinstance(other, Step):
            return NotImplemented
        if self.id != other.id:
            raise Exception("Cannot merge two steps with different numbers")
        return Step(
            self.id,
            self.fixpoint_h or other.fixpoint_h,
            self.fixpoint_t or other.fixpoint_t,
            self.interpretation + other.interpretation,
            self.symbols + other.symbols
        )


@dataclass
class StepSequence(Sequence):
    "Given a complete sequence of partial steps, compute the sorted sequence of complete steps"

    __data: tuple = field(init=False)


    def __init__(self, steps: Iterable[Step]):
        super().__init__()
        self.__data = tuple(
            reduce(add, substeps) for _, substeps in groupby(sorted(steps))
        )

    def __len__(self):
        return self.__data.__len__()

    def __getitem__(self, key):
        return self.__data.__getitem__(key)

    def compute_padding(self) -> "tuple[int, int]":
        padding = [0, 0]
        for step in self:
            step_padding = step.compute_padding()
            for i in range(2):
                padding[i] = max(padding[i], step_padding[i])
        return (padding[0], padding[1])

    def __add__(self, other):
        return StepSequence(self.__data + other.__data)

    def unchain(self):
        return map(itemgetter(1), groupby(self, key=lambda x: (x.id[0],) * len(x.id)))

    @property
    def interpretation(self):
        if len(self) == 0:
            return Interpretation()
        return self[0].interpretation

    @staticmethod
    def from_atoms(symbols: Iterable[Symbol]) -> "StepSequence":
        return StepSequence(filter(is_not_none, (Step.from_atom(symbol) for symbol in symbols)))

@dataclass
class AnswerSet:
    """A wrapper around models that is aware of the 'step' and model 'arguments'
    Provides mechanisms to print data nicely

    Construct using StepSequcence.from_atoms which will create a sequence of Steps
    Combine multiple partial sequences with + to obtain a complete sequence"""

    steps: "StepSequence"

    def __init__(self, model: "Model"):
        self.steps = StepSequence.from_atoms(model.symbols(atoms=True))

    @property
    def interpretation(self):
        return self.steps.interpretation

    @staticmethod
    def __solve(program: str, step_program: "str | None" = None, all_models: bool = False) -> "AnswerSet | Iterable[AnswerSet]":
        """Handles all invocations of clingo solving
        providing step_program will enable incremental mode
        """
        ctl = Control(["--models=0"] if all_models else [])
        if step_program is None:
            ctl.add(program)
        else:
            assert not all_models, "incremental solving will return the first model"
            ctl.add("base", [], program)
            ctl.add("step", ["incremental"], step_program)
        ctl.ground()

        if all_models:
            return tuple(
                AnswerSet(model) for model in ctl.solve(yield_=True)
            )
        # Incremental solving doesn't play nice with yield_
        # But we only need one model
        answerset = None
        def on_model(model: "Model"):
            nonlocal answerset
            answerset = AnswerSet(model)

        if step_program is None:
            ctl.solve(on_model=on_model)
            return answerset

        # Incremental solving
        for i in count():
            ctl.ground([("step", [Number(i)])])
            ctl.solve(on_model=on_model)
            if answerset is not None:
                return answerset




    @classmethod
    def solve_one(cls, program: str) -> "AnswerSet":
        return cls.__solve(program)

    @classmethod
    def solve_all(cls, program: str) -> "Iterable[AnswerSet]":
        return sorted(cls.__solve(program, all_models=True), key=attrgetter("interpretation"))


    @classmethod
    def solve_incremental(cls, base: str, step: str) -> "AnswerSet":
        return cls.__solve(base, step_program=step)

    @staticmethod
    def compute_padding(answersets: "Iterable[AnswerSet]") -> "tuple[int, int]":
        answersets = tuple(answersets)
        if len(answersets) == 0:
            return (0, 0)
        return reduce(add, map(attrgetter("steps"), answersets)).compute_padding()

    def atoms_text(self) -> str:
        "Gathers the text for the atoms in the answer set"
        return "\n".join(str(symbol)
            for step in self.steps
            for symbol in step.symbols)

    def stable_steps(self, padding: "tuple[int, int] | None" = None):
        result = StringIO()
        if padding is None:
            padding = self.steps.compute_padding()
        for substeps in self.steps.unchain():
            for step in substeps:
                result.write(step.interpretation_padded_string(padding))
                result.write("\n")
                if step.is_fixpoint():
                    break
        return result.getvalue()

    def fixpoint(self, padding: "tuple[int, int] | None" = None):
        if padding is None:
            padding = self.steps.compute_padding()
        i = self.steps[-1].interpretation
        return f"FIXPOINT {i.padded_string(padding)}"
    
    @staticmethod
    def fixpoints(answersets: "Iterable[AnswerSet]", show_answer_set: bool, output_file):
        padding = AnswerSet.compute_padding(answersets)
        for answerset in answersets:
            if show_answer_set:
                print(answerset.fixpoint(padding), file=output_file)
                print(answerset.atoms_text(), file=output_file)
            print(answerset.fixpoint(padding), file=output_file)
            if show_answer_set:
                print(file=output_file)




def load_from_file(file: Path) -> str:
    return f"""
%!! Loaded from '{file}'
{file.read_text()}
    """





STDIN_CACHE = None
def read_possibly_stdin(path: Path) -> str:
    "Read text contents of file at path or from stdin if path is '-"
    global STDIN_CACHE
    if str(path) == "-":
        if STDIN_CACHE is None:
            STDIN_CACHE = stdin.read()
        return STDIN_CACHE
    else:
        return path.read_text()


def step_lt_step(a: tuple, b: tuple) -> bool:
    "Defines the ordering for two step numbers, e.g. (1,2) < (1,) < (2, 4)"
    length = max(len(a), len(b))
    a += (length - len(a)) * (inf,)
    b += (length - len(b)) * (inf,)
    return a < b


def get_step_arg(symbol: Symbol) -> "tuple | None":
    "func(X, J, step(42, 7)) => (42, 7)"
    return next((
        tuple(step.number for step in arg.arguments)
        for arg in symbol.arguments
        if arg.type is SymbolType.Function and arg.name == "step"
    ), None)


def get_model_arg(symbol: Symbol) -> "str | None":
    "func(X, J, model(h)) => 'h'"
    return next((
        arg.arguments[0].name
        for arg in symbol.arguments
        if arg.type is SymbolType.Function and arg.name == "model"
    ), None)


def reify_into_program_text(program: str) -> str:
    """Works like reify_program, but returns a program's text
    Instead of symbols"""
    header = "\n%!! Generated from reifying input program\n"
    rules = "\n".join(f"{fact}." for fact in reify_program(program))
    return header + rules


def rules_into_text(src: Path, rules: Sequence[AST]) -> str:
    result = "\n".join(map(str, rules))
    return f"""
%!! Program generated using the base '{src}'
{result}
"""


def iterate_models(program: str, num_models: int = 0):
    # Bug in Clingo requires that the control and solve handle be kept together
    # https://github.com/potassco/clingo/issues/561
    # TODO remove from return when fixed
    ctl = Control([f"--models={num_models}"])
    ctl.add(program)
    ctl.ground()
    return ctl, ctl.solve(yield_=True, on_unsat=print)


def output_file_default(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "output_file" not in kwargs:
            kwargs["output_file"] = stdout
        return fn(*args, **kwargs)
    return wrapper


@output_file_default
@app.command()
def solve(filenames: List[Path], output_file=OUTPUT_FILE):
    "A minimal frontend around clingo that prints atoms out sorted by steps"
    data = "\n".join(
        read_possibly_stdin(filename)
        for filename in filenames
    )
    answerset = AnswerSet.solve_one(data)
    if answerset is None:
        print("No answer set", file=output_file)
    else:
        print(answerset.atoms_text(), file=output_file)


@output_file_default
@app.command()
def well_founded(operator: Path, program: Optional[Path] = None, solve: bool = True, show_answer_set: bool = SHOW_ANSWER_SET_OPTION, *, output_file = OUTPUT_FILE):
    "Construct the stable operator for a given operator to compute the well-founded fixpoint"
    from transforms.create_stable_operator import create_stable_operator

    if program is None:
        solve = False

    rules = parse_rules(read_possibly_stdin(operator))
    rules = create_stable_operator(rules)
    output = rules_into_text(operator, rules)
    p = Path(__file__).parent
    output += load_from_file(p / "axioms/fixpoints/iterate_generic_1step.lp")
    output += load_from_file(p / "axioms/fixpoints/iterate_generic_2step.lp")
    output += load_from_file(p / "axioms/fixpoints/iterate_lfp.lp")
    output += load_from_file(p / "axioms/fixpoints/1step.lp")
    output += load_from_file(p / "axioms/fixpoints/2step.lp")
    output += load_from_file(p / "axioms/output_1step.lp")
    output += load_from_file(p / "axioms/output_2step.lp")
    output += load_from_file(p / "axioms/models.lp")
    output += load_from_file(p / "axioms/all_1steps.lp")
    output += load_from_file(p / "axioms/all_2steps.lp")
    if program is not None:
        output += reify_into_program_text(program.read_text())
    if not solve:
        print(output, file=output_file)
        return

    answerset = AnswerSet.solve_one(output)

    if show_answer_set:
        print(answerset.atoms_text(), file=output_file)

    print(answerset.stable_steps(), file=output_file)



def fixpoints_helper(operator: Path, program: Optional[Path] = None):
    "Enumerate the fixpoints of a given operator"
    from transforms.create_fixpoints_operator import create_fixpoints_operator

    rules = parse_rules(read_possibly_stdin(operator))
    rules = create_fixpoints_operator(rules)

    output = rules_into_text(operator, rules)
    p = Path(__file__).parent
    output += load_from_file(p / "axioms/fixpoints/1step.lp")
    output += load_from_file(p / "axioms/fixpoints/iterate_generic_1step.lp")
    output += load_from_file(p / "axioms/output_1step.lp")
    output += load_from_file(p / "axioms/models.lp")

    if program is not None:
        output += reify_into_program_text(program.read_text())

    return output



@output_file_default
@app.command()
def fixpoints(operator: Path, program: Optional[Path] = None, solve: bool = True, show_answer_set: bool = SHOW_ANSWER_SET_OPTION, *, output_file=OUTPUT_FILE):
    "Enumerate the fixpoints of a given operator"

    full_program = fixpoints_helper(operator, program)
    p = Path(__file__).parent
    full_program += load_from_file(p /
                                   "axioms/fixpoints/iterate_everything.lp")

    if program is None or not solve:
        print(full_program, file=output_file)
        return

    answersets = AnswerSet.solve_all(full_program)
    AnswerSet.fixpoints(answersets, show_answer_set, output_file)

@app.command()
def stable_fixpoints(operator: Path, program: Optional[Path] = None, solve: bool = True, show_answer_set: bool = SHOW_ANSWER_SET_OPTION, output_file=OUTPUT_FILE):
    "Construct the stable operator for a given operator to compute all fixpoints"
    from transforms.create_stable_operator import create_stable_operator

    if program is None:
        solve = False

    rules = parse_rules(read_possibly_stdin(operator))
    rules = create_stable_operator(rules)
    full_program = rules_into_text(operator, rules)
    p = Path(__file__).parent
    full_program += load_from_file(p / "axioms/fixpoints/iterate_generic_1step.lp")
    full_program += load_from_file(p / "axioms/fixpoints/iterate_generic_2step.lp")
    full_program += load_from_file(p / "axioms/fixpoints/iterate_everything.lp")
    full_program += load_from_file(p / "axioms/fixpoints/1step.lp")
    full_program += load_from_file(p / "axioms/fixpoints/2step.lp")
    full_program += load_from_file(p / "axioms/output_1step.lp")
    full_program += load_from_file(p / "axioms/output_2step.lp")
    full_program += load_from_file(p / "axioms/models.lp")
    # We only need all_2steps because iterate_everything.lp provides 1steps
    full_program += load_from_file(p / "axioms/all_2steps.lp")
    if program is not None:
        full_program += reify_into_program_text(program.read_text())
    if not solve:
        print(full_program, file=output_file)
        return

    answersets = AnswerSet.solve_all(full_program)
    padding = AnswerSet.compute_padding(answersets)
    for answerset in answersets:
        if show_answer_set:
            print(answerset.fixpoint(padding), file=output_file)
            print(answerset.atoms_text(), file=output_file)
        print(answerset.fixpoint(padding), file=output_file)
        if show_answer_set:
            print(file=output_file)

    # solve_print_steps(full_program, partial(print_stable_model,
                      # show_answer_set=show_answer_set))


@output_file_default
@app.command()
def kripke_kleene(operator: Path, program: Optional[Path] = None, solve: bool = True, show_answer_set: bool = SHOW_ANSWER_SET_OPTION, incremental: bool = INCREMENTAL_OPTION, *, output_file=OUTPUT_FILE):
    "Compute the Kripke Kleene fixpoint"

    full_program = fixpoints_helper(operator, program)
    p = Path(__file__).parent
    full_program += load_from_file(p / "axioms/fixpoints/iterate_lfp.lp")
    full_program += load_from_file(p / "axioms/all_1steps.lp")

    if incremental:
        full_program += load_from_file(p /
                                       "axioms/fixpoints/iterate_incremental.lp")
    if program is None or not solve:
        print(full_program, file=output_file)
        return

    if incremental:
        answerset = AnswerSet.solve_incremental("", full_program)
    else:
        answerset = AnswerSet.solve_one(full_program)
    padding = AnswerSet.compute_padding((answerset,))

    if show_answer_set:
        print(answerset.fixpoint(padding), file=output_file)
        print(answerset.atoms_text(), file=output_file)
    print(answerset.fixpoint(padding), file=output_file)


@output_file_default
@app.command()
def verify_syntax(program: Path, *, output_file=OUTPUT_FILE):
    "Checks whether program contains unsupported syntax features. (NOTE: this is not complete and will only catch *some* unsupported syntax)"

    from transforms.syntax_verifier import verify, UnsupportedSyntax

    rules = parse_rules(read_possibly_stdin(program))

    try:
        for rule in rules:
            verify(rule)
    except UnsupportedSyntax as e:
        print(e, file=output_file)
    else:
        print("Syntax seems fine.", file=output_file)


def ultimate_helper(program: Path, solve: bool, show_answer_set: bool, output_file, additional_files: "Tuple[str]", many: bool):
    p = Path(__file__).parent
    output = reify_into_program_text(program.read_text())
    output += load_from_file(p / "ultimate/ultimate_operator_binary.lp")
    output += load_from_file(p / "axioms/fixpoints/1step.lp")
    output += load_from_file(p / "axioms/fixpoints/iterate_generic_1step.lp")
    output += load_from_file(p / "axioms/output_1step.lp")
    output += load_from_file(p / "axioms/models.lp")
    output += "\n".join(additional_files)
    show_answer_set = bool(show_answer_set) if show_answer_set != "False" else False
    if not solve:
        print(output, file=output_file)
        return
    if not many:
        answerset = AnswerSet.solve_one(output)
        if answerset is None:
            print("No fixpoints", file=output_file)
            return
        if show_answer_set is True:
            print(answerset.atoms_text(), file=output_file)
        print(answerset.fixpoint(), file=output_file)    
        return
    answersets = AnswerSet.solve_all(output)
    AnswerSet.fixpoints(answersets, show_answer_set, output_file)

@app.command()
def ultimate_kripke_kleene(program: Path, solve: bool=True, show_answer_set=SHOW_ANSWER_SET_OPTION, output_file=OUTPUT_FILE):
    "Construct the ultimate operator for the Melvin-Fitting operator applied to a program to compute the Kripke-Kleene fixpoint"
    p = Path(__file__).parent 
    file = load_from_file(p / "axioms/fixpoints/iterate_lfp.lp")
    file += load_from_file(p / "axioms/all_1steps.lp")
    ultimate_helper(program, solve, show_answer_set, output_file, (file,), False)

@app.command()
def ultimate_fixpoints(program: Path, solve: bool=True, show_answer_set=SHOW_ANSWER_SET_OPTION, output_file=OUTPUT_FILE):
    "Construct the ultimate operator for the Melvin-Fitting operator applied to a program to compute all fixpoints"
    file = load_from_file(Path(__file__).parent / "axioms/fixpoints/iterate_everything.lp")
    ultimate_helper(program, solve, show_answer_set, output_file, (file,), True)

@app.command()
def regression_test(accept: bool = ACCEPT_TESTS_OPTION):
    "Run all the regression tests and compare their output to the accepted output. Run with --accept to make current output accepted."
    p = Path(__file__).parent
    fitting = p / "operators/fitting.lp"

    def new_path(test): return Path(f"{test}.new_test_output")
    def accepted_path(test): return Path(f"{test}.accepted_test_output")

    def accept_output():
        for test in Path.glob(p / "tests", "*.lp"):
            new = new_path(test)
            if new.exists():
                new.replace(accepted_path(test))
    if accept:
        return accept_output()

    for test in Path.glob(p / "tests", "*.lp"):
        print("Testing file:", f"'{test}'", file=stderr)
        with open(new_path(test), "wt", encoding="utf-8") as new_output:
            print(
                f"kripke_kleene(operator=Path('{fitting}'), program=Path('{test}'), solve=True, show_answer_set=False, incremental=False)", file=new_output)
            kripke_kleene(fitting, test, solve=True, show_answer_set=False, incremental=False, output_file=new_output)
            print(
                f"fixpoints(operator=Path('{fitting}'), program=Path('{test}'), solve=True, show_answer_set=False)", file=new_output)
            fixpoints(fitting, test, solve=True, show_answer_set=False, output_file=new_output)
            print(
                f"well_founded(operator=Path('{fitting}'), program=Path('{test}'), solve=True, show_answer_set=False)", file=new_output)
            well_founded(fitting, test, True, False, output_file=new_output)
            print(
                f"stable_fixpoints(operator=Path('{fitting}'), program=Path('{test}'), solve=True, show_answer_set=False)", file=new_output)
            stable_fixpoints(fitting, test, True, False, output_file=new_output)
            print(
                f"ultimate_kripke_kleene(program=Path('{test}'), solve=True, show_answer_set=False)", file=new_output)
            ultimate_kripke_kleene(test, True, False, output_file=new_output)
            print(
                f"ultimate_fixpoints(program=Path('{test}'), solve=True, show_answer_set=False)", file=new_output)
            ultimate_fixpoints(test, True, False, output_file=new_output)

    some_differ = False
    for test in Path.glob(p / "tests", "*.lp"):
        new = new_path(test)
        accepted = accepted_path(test)
        if not accepted.exists():
            continue
        if new.read_text() != accepted.read_text():
            print(f"Files '{new}' and '{accepted}' differ", file=stderr)
            some_differ = True
    if not some_differ:
        print("All outputs are the same as accepted output", file=stderr)
        accept_output()
    else:
        raise typer.Exit(code=1)


if __name__ == "__main__" and not sys.flags.interactive:
    app()
