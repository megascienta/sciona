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
                return self.callable_qname_by_span.get(key)
            current = getattr(current, "parent", None)
        return None


__all__ = ["STRUCTURAL_CALLABLE_NODE_TYPES", "ScopeResolver"]
