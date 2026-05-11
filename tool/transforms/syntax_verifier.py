"""
Verify, for sanity purposes, that input program is not relying upon unsupported features
Such as dijunction or constraints.
"""

from clingo.ast import Rule, AST, ASTType
from .util import full_tree

UNPERMITTED_NODE_TYPES = (ASTType.Disjunction,)


class UnsupportedSyntax(Exception):
    pass


def verify(rule: Rule) -> Rule:
    for node in full_tree(rule):
        if node.ast_type in UNPERMITTED_NODE_TYPES:
            raise UnsupportedSyntax(f"Unpermitted node type: {node.ast_type}")
        if is_constraint(node):
            raise UnsupportedSyntax("Constraints are not supported")
    return rule


def is_constraint(node: AST):
    """
    Checks whether the rule is a constraint
    E.g.
    :- a.
    As of clingo 5.6.2, this is represented as
    #false :- a.
    """
    return node.ast_type == ASTType.Rule and is_false_literal(node.head)


def is_false_literal(node: AST):
    "Checks whether the node is #false wrapped as a literal"
    return node.ast_type == ASTType.Literal and \
        node.atom.ast_type == ASTType.BooleanConstant and \
        node.atom.value == 0
