"""
Accepts a logic program and changes increases all "step" in the given rule heads
Eg.
foo(step(1, 2)) :- foo(step(1, 2)), step(1, 2) => foo(step(1, 2+1)) :- foo(step(1, 2)), step(1, 2+1).

Arguments:
step_dimensionality: only target step functions with the appropriate number of dimensions
step_index: which dim of the step function to increase
atom_name/arity: 1 or more atom/arity pairs to replace

Usage:

python -m transforms.increase_head_step <step_dimensionality> <step_index> <atom_name/arity> <atom_name/arity> <atom_name/arity> ... < input_program.lp

Ouput:
Just the rules are written to stdout
"""

from sys import stdin, argv, flags
from clingo.ast import AST, ASTType, BinaryOperation, BinaryOperator, SymbolicTerm
from clingo.symbol import Number
from .iter_transformer import transform
from .util import TargetAtom, StepConfig, SYNTHETIC_LOCATION, parse_rules
from typing import Container, Iterable


def increment_head_step(ast: AST, targets: Container[TargetAtom], step: StepConfig, index: int) -> AST:
    rule_transform = transform(ast, [ASTType.Rule])
    for rule, update_rule in rule_transform:
        incremented_head_step = False
        head_transform = transform(rule.head, [ASTType.Function])
        for func, update_head in head_transform:
            if TargetAtom.from_function(func) in targets:
                incremented_head_step = True
                update_head(increment_step_arg(func, step, index))
        if incremented_head_step:
            update_rule(rule.update(
                head=head_transform.node,
                body=[
                    increment_step_func_lit(lit, index)
                    if step.is_function_lit(lit)
                    else lit
                    for lit in rule.body
                ]
            ))
    return rule_transform.node


def increment_step_arg(func: AST, step: StepConfig, index: int) -> AST:
    "If a function (e.g. hold(step(1, 2))) contains step func arg, increment it"
    return func.update(arguments=[
        increment_step_func(node, index)
        if step.is_function(node)
        else node
        for node in func.arguments
    ])


def increment_step_func_lit(lit: AST, index: int) -> AST:
    "Increment a step function inside a literal (e.g. postive atom in a rule body)"
    return lit.update(
        atom=lit.atom.update(
            symbol=increment_step_func(lit.atom.symbol, index)
        )
    )


def increment_step_func(func: AST, index: int) -> AST:
    args = list(func.arguments)
    args[index] = BinaryOperation(
        location=SYNTHETIC_LOCATION,
        operator_type=BinaryOperator.Plus,
        left=args[index],
        right=SymbolicTerm(SYNTHETIC_LOCATION, Number(1)),
    )
    return func.update(arguments=args)


def main(program_text: str, dimensionality: int, step_index: int, target_atoms: Iterable[TargetAtom]):
    rules = parse_rules(program_text)
    rules = increment_head_step(
        rules, target_atoms, StepConfig(dimensionality), step_index)
    print(*rules, sep="\n")


if __name__ == "__main__" and not flags.interactive:
    assert len(
        argv) >= 4, "Program accepts 3 arguments at minimum: <step_dimensionality> <step_index> <atom_name/arity>"
    program_text = stdin.read()
    dimensionality = int(argv[1])
    step_index = int(argv[2])
    arg_pairs = (arg.split("/") for arg in argv[3:])
    target_atoms = (TargetAtom(name, int(arity)) for name, arity in arg_pairs)
    main(program_text, dimensionality, step_index, target_atoms)

