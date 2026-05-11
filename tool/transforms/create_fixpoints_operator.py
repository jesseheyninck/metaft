"""
Given a program that defined an operator using hold(A, model(M))
Construct a program that computes fixpoints for the operator
See operators/fitting.lp for operator example

Usage:
python -m transforms.create_fixpoints_operator < operator.lp

"""

from sys import flags, stdin
from typing import Sequence
from clingo.ast import AST
from .increment_head_step import increment_head_step
from .util import StepConfig, TargetAtom, parse_rules
from .make_stepped import make_stepped, expand_targets


def create_fixpoints_operator(rules: Sequence[AST], target = TargetAtom("hold", 2)) -> AST:
    step_targets = expand_targets(rules, [target])
    step = StepConfig(1)
    rules = make_stepped(rules, step_targets, step)
    target = TargetAtom(target.name, target.arity + 1)
    rules = increment_head_step(rules, [target], step, 0)

    return rules


def main(program: str):
    rules = parse_rules(program)
    rules = create_fixpoints_operator(rules)
    print(*rules, sep="\n")

if __name__ == "__main__" and not flags.interactive:
    program_text = stdin.read()
    main(program_text)
