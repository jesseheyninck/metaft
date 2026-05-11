"""
Given a program that defined an operator using hold(A, model(M))
Construct a stable operator from it.
See operators/fitting.lp for operator example

Usage:
python -m transforms.create_stable_operator < operator.lp

"""
from sys import flags, stdin
from typing import Sequence
from clingo.symbol import Number
from clingo.ast import AST, ASTType, BinaryOperation, BinaryOperator, SymbolicTerm
from .util import parse_rules, StepConfig, TargetAtom, SYNTHETIC_LOCATION
from .make_stepped import make_stepped, expand_targets
from .increment_head_step import increment_head_step
from .iter_transformer import transform


def create_stable_operator(rules: Sequence[AST], target: TargetAtom = TargetAtom("hold", 2)) -> AST:
    step_targets = expand_targets(rules, [target])
    step = StepConfig(2)
    rules = make_stepped(rules, step_targets, step)
    new_target = TargetAtom(target.name, target.arity + 1)
    rules = increment_head_step(rules, [new_target], step, 1)

    rules = transform(rules, [ASTType.Rule])
    for rule, update_rule in rules:
        head_model = None
        for func, _ in transform(rule.head, [ASTType.Function]):
            head_model = get_model_arg(func)
        if head_model is None:
            continue
        body = transform(rule.body, [ASTType.Function])
        for func, update_body in body:
            body_model = get_model_arg(func)
            if body_model == head_model:
                continue
            update_body(func.update(
                arguments=[
                    decrement_step(arg)
                    if step.is_function(arg)
                    else arg
                    for arg in func.arguments
                ]
            ))
        update_rule(rule.update(
            body=body.node
        ))

    return rules.node


def decrement_step(func: AST) -> AST:
    """
    Decrements a step function and lower its arity
    step(1, 2) => step((1-1))
    """
    return func.update(arguments=[BinaryOperation(
        location=SYNTHETIC_LOCATION,
        operator_type=BinaryOperator.Minus,
        left=func.arguments[0],
        right=SymbolicTerm(SYNTHETIC_LOCATION, Number(1)),
    )])


def get_model_arg(func: AST) -> str:
    """
    Given a func: model(h) or model(t) return "h" or "t" respectively
    Otherwise return None
    """
    model = TargetAtom("model", 1)
    for arg in func.arguments:
        if arg.ast_type != ASTType.Function or TargetAtom.from_function(arg) != model:
            continue
        model = arg.arguments[0]
        if model.ast_type is ASTType.Variable:
            raise Exception(f"Model not grounded '{model}'")
        return str(model.symbol)
    return None


def main(program_text: str):
    rules = parse_rules(program_text)
    rules = create_stable_operator(rules)
    print(*rules, sep="\n")


if __name__ == "__main__" and not flags.interactive:
    program_text = stdin.read()
    main(program_text)
