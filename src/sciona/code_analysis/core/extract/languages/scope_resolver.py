# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Ancestry-based callable scope resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


STRUCTURAL_CALLABLE_NODE_TYPES = frozenset(
    {
        # Python
        "function_definition",
        "async_function_definition",
        # TypeScript
        "method_definition",
        "function_declaration",
        # Java
        "method_declaration",
        "constructor_declaration",
        "compact_constructor_declaration",
    }
)


@dataclass(frozen=True)
class ScopeResolver:
    """Resolve nearest enclosing structural callable via node ancestry."""

    callable_qname_by_span: Mapping[tuple[int, int], str]

    def enclosing_callable(self, node) -> str | None:
        current = getattr(node, "parent", None)
        while current is not None:
            if current.type in STRUCTURAL_CALLABLE_NODE_TYPES:
                key = (current.start_byte, current.end_byte)
                resolved = self.callable_qname_by_span.get(key)
                if resolved is not None:
                    return resolved
            current = getattr(current, "parent", None)
        return None

    def enclosing_callable_for_span(
        self,
        *,
        root,
        call_span: tuple[int, int],
    ) -> str | None:
        call_node = _find_node_by_span(root, call_span)
        if call_node is None:
            return None
        return self.enclosing_callable(call_node)


def _find_node_by_span(root, span: tuple[int, int]):
    start_byte, end_byte = span
    stack = [root]
    while stack:
        node = stack.pop()
        if node.start_byte == start_byte and node.end_byte == end_byte:
            return node
        for child in getattr(node, "children", []):
            if child.start_byte <= start_byte and child.end_byte >= end_byte:
                stack.append(child)
    return None


__all__ = ["STRUCTURAL_CALLABLE_NODE_TYPES", "ScopeResolver"]
