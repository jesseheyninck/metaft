import clingo
from clingo.ast import AST, Transformer, Location, Position, ASTType, Function, Variable, Literal, SymbolicAtom, Sign
from typing import Callable, Generator, Iterable, Container, Sequence
from itertools import chain, count
from dataclasses import dataclass

SYNTHETIC_POSITION = Position(filename="<string>", line=1, column=1)
SYNTHETIC_LOCATION = Location(begin=SYNTHETIC_POSITION, end=SYNTHETIC_POSITION)


class VariableNameCollector(Transformer):
    def __init__(self):
        self.variables = set()

    def visit_Variable(self, variable: AST):
        self.variables.add(variable.name)
        return variable


def variable_names(scope: AST) -> Container[str]:
    "Returns the variable names that appear in the given ast"
    collector = VariableNameCollector()
    collector(scope)
    return frozenset(collector.variables)


def unique_variable_names(names: Iterable[str], scope: AST) -> Iterable[str]:
    """
    Returns the variable names from names that do not appear within the AST scope
    """
    return (name for name in names if name not in variable_names(scope))


def parse_rules(program_text: str) -> "tuple[AST, ...]":
    "Parse a program and return just the rules"
    parts = []
    clingo.ast.parse_string(program_text, parts.append)
    return tuple(part for part in parts if part.ast_type is ASTType.Rule)


@dataclass(frozen=True)
class StepConfig:
    dimensionality: int
    atom_name = "step"
    variable_template = "S"

    def variable_names(self):
        "Generate possible names for the step variable: S1, S2, S3, ... etc"
        if self.dimensionality == 1:
            yield self.variable_template
        for i in count(1):
            yield f"{self.variable_template}{i}"

    def function(self, var_names: str) -> AST:
        "Generate the function to be added as an arg to a function"
        return Function(
            location=SYNTHETIC_LOCATION,
            name=self.atom_name,
            arguments=[Variable(
                location=SYNTHETIC_LOCATION,
                name=var_name,
            ) for var_name in var_names],
            external=False,
        )

    def is_function(self, node: AST) -> bool:
        """
        Checks whether node resembles something returned from self.function
        Variables are ignored
        """
        return node.ast_type == ASTType.Function and TargetAtom.from_function(node) == TargetAtom.from_step(self)

    def function_lit(self, var_names: str) -> AST:
        "Generate the function to be added to the body of a function"
        return Literal(
            location=SYNTHETIC_LOCATION,
            sign=Sign.NoSign,
            atom=SymbolicAtom(self.function(var_names))
        )

    def is_function_lit(self, node: AST) -> bool:
        """
        Checks whether node resembles something returned from self.function_lit
        Variables are ignored
        """
        return (node.ast_type is ASTType.Literal and
                node.sign == Sign.NoSign and
                node.atom.ast_type is ASTType.SymbolicAtom and
                node.atom.symbol.ast_type is ASTType.Function and
                self.is_function(node.atom.symbol))


@dataclass(frozen=True)
class TargetAtom:
    name: str
    arity: int

    @staticmethod
    def from_function(func: AST) -> "TargetAtom":
        return TargetAtom(func.name, len(func.arguments))

    @staticmethod
    def from_step(step: StepConfig) -> "TargetAtom":
        return TargetAtom(step.atom_name, step.dimensionality)


def get_function_function(function: AST, subfunction: TargetAtom) -> "tuple[AST, Callable[[AST], AST]] | None":
    """
    Given a function e.g. hold(1, 2, model(h)) and a target model/1
    Return the first model(h) if it's a direct argument of function
    Is also paired with a function to update the function passed as an argument

    Otherwise None
    """
    assert function.ast_type is ASTType.Function
    for i, arg in enumerate(function):
        if arg.ast_type is ASTType.Function and TargetAtom.from_function(arg) == subfunction:
            def update(func: AST):
                assert func.ast_type is ASTType.Function

            return arg


def get_function_model(function: AST) -> "str | None":
    """
    Given a function e.g. hold(1, 2, model(h))
    Return "h" if it's a direct argument of function
    Otherwise None
    """
    func = get_function_function(function, TargetAtom("model", 1))
    if func is None:
        return None
    print(func.arguments[0])
    exit(0)


def with_send(gen: Generator) -> Iterable:
    """
    Iterate pairs (x, send) where gen produces x and send is gen's send function
    If send is not called in an iteration, then next() is used to advance gen
    """
    try:
        next_buffer = None
        next_exception = None

        def send(v):
            nonlocal next_buffer, next_exception
            assert next_buffer is None and next_exception is None, "send function called multiple times?"
            try:
                next_buffer = gen.send(v)
            except StopIteration as s:
                next_exception = s
        yield (next(gen), send)
        while True:
            if next_exception:
                return next_exception.value
            if next_buffer is not None:
                v, next_buffer = next_buffer, None
                yield (v, send)
            else:
                yield (next(gen), send)
    except StopIteration as s:
        return s.value
    except GeneratorExit:
        gen.close()


def full_tree(node: "AST | Sequence") -> "Iterable[AST]":
    if isinstance(node, Sequence):
        yield from chain.from_iterable(full_tree(child) for child in node)
        return
    yield node
    yield from chain.from_iterable(full_tree(getattr(node, key)) for key in node.child_keys)
