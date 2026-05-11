"""
Accepts a logic program containing an operator and creates a new program where predicates have an additional "step" parameter added to the end
E.g.
conjunction(B, t). => conjunction(B, t, step(Step)) :- step(Step).

Arguments:
step_dimensionality: the number of args for the step function. e.g. 2 -> step(Step1, Step2)
atom_name/arity: 1 or more atom/arity pairs to replace

Usage:

python -m transforms.make_stepped <step_dimensionality> <atom_name/arity> <atom_name/arity> <atom_name/arity> ... < input_program.lp

Ouput:
Just the rules are written to stdout
"""

from sys import stdin, argv, flags
from clingo.ast import AST, ASTType
from itertools import islice
from typing import Iterable
from .util import unique_variable_names, parse_rules, TargetAtom, StepConfig
from .iter_transformer import transform


def make_stepped(ast: AST, targets: "tuple[TargetAtom, ...]", step: StepConfig) -> AST:
    "Converts rules by adding a 'step' argument to the given target atoms"

    rule_transform = transform(ast, [ASTType.Rule])
    for rule, update_rule in rule_transform:
        step_vars = tuple(islice(unique_variable_names(
            step.variable_names(), rule), step.dimensionality))

        body_transform = transform(rule.body, [ASTType.Function])
        for func, update_body in body_transform:
            if TargetAtom.from_function(func) in targets:
                update_body(func.update(
                    arguments=[*func.arguments, step.function(step_vars)]))

        target_in_head = False
        head_transform = transform(rule.head, [ASTType.Function])
        for func, update_head in head_transform:
            if TargetAtom.from_function(func) in targets:
                target_in_head = True
                update_head(func.update(
                    arguments=[*func.arguments, step.function(step_vars)]))
        if target_in_head:
            update_rule(rule.update(
                head=head_transform.node,
                body=[
                    step.function_lit(step_vars),
                    *body_transform.node,
                ]))
        else:
            update_rule(rule.update(body=body_transform.node))

    return rule_transform.node


def expand_targets(ast: AST, targets: "tuple[TargetAtom, ...]"):
    targets = set(targets)
    prev = None
    while targets != prev:
        prev = set(targets)
        for rule, _ in transform(ast, [ASTType.Rule]):
            target_appears_in_body = any(TargetAtom.from_function(node) in targets
                                         for node, _ in transform(rule.body, [ASTType.Function]))
            if target_appears_in_body:
                funcs_in_head = (node for node, _ in transform(
                    rule.head, [ASTType.Function]))
                targets.update(map(TargetAtom.from_function, funcs_in_head))
    return targets


def main(program_text: str, dimensionality: int, target_atoms: Iterable[TargetAtom]):
    rules = parse_rules(program_text)
    target_atoms = expand_targets(rules, target_atoms)
    rules = make_stepped(rules, target_atoms, StepConfig(dimensionality))

    print(*rules, sep="\n")


if __name__ == "__main__" and not flags.interactive:
    assert len(
        argv) >= 3, "Program accepts 2 arguments at minimum: <dimensionality> <atom_name/arity>"
    program_text = stdin.read()
    dimensionality = int(argv[1])
    arg_pairs = (arg.split("/") for arg in argv[2:])
    target_atoms = (TargetAtom(name, int(arity)) for name, arity in arg_pairs)
    main(program_text, dimensionality, target_atoms)
