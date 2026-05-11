"""
An alternative to clingo's built-in AST transformer to make find and replace operations easier and much more succinct 
"""

from clingo.ast import ASTType, AST
from typing import Generator, Sequence
from dataclasses import dataclass
from .util import with_send


@dataclass
class transform:
    """
    Generator that follows implementation of clingo.ast.Transform
    Instead of defining visitor methods, users iterate nodes and update() to update the nodes
    Nested matches are not iterated

    node: the ast node to iterate (updated after this is iterated)
    types: will skip nodes not in types

    Usage:
        for node, update in transform(ast, [clingo.ast.ASTType.Function]):
            update(new_node)
    """
    node: "AST | Sequence[AST]"
    types: "tuple[ASTType, ...] | None"

    def __iter__(self):
        return with_send(self.manual())

    def is_wanted_type(self, ast: AST) -> bool:
        return (not isinstance(ast, Sequence)) and (ast.ast_type in self.types)

    def manual(self) -> Generator[AST, AST, "AST | Sequence[AST]"]:
        """
        Creates a generator that yields a node, then expects a node to replace it to be sent back
        If the value None is sent, then the original node is kept
        (This allows this iterator to be used in a regular for loop without replacing nodes)
        """
        if isinstance(self.node, Sequence):
            # Would use a list comprehension, but Python syntax won't allow it :(
            updated = []
            for node in self.node:
                updated.append((yield from transform(node, self.types).manual()))
            self.node = updated
            return self.node
        if self.is_wanted_type(self.node):
            self.node = (yield self.node) or self.node
            return self.node
        # Following clingo.ast.Transform.visit_children
        updates = {}
        for key in self.node.child_keys:
            old = getattr(self.node, key)
            new = (yield from transform(old, self.types).manual())
            if new is not old:
                updates[key] = new
        self.node = self.node.update(**updates)
        return self.node
    
