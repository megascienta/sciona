# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared tree-sitter parse validation helpers."""

from __future__ import annotations


class ParseValidationError(ValueError):
    """Raised when a parsed tree contains syntax error markers."""


def validate_tree_or_raise(tree, *, language_name: str) -> None:
    root = getattr(tree, "root_node", None)
    if root is None:
        raise ParseValidationError(
            f"Tree-sitter parse validation failed for {language_name}: missing root node"
        )

    error_examples: list[str] = []
    error_count = 0
    missing_count = 0
    stack = [root]
    while stack:
        node = stack.pop()
        node_type = getattr(node, "type", "")
        if node_type == "ERROR":
            error_count += 1
            if len(error_examples) < 3:
                error_examples.append(_format_node_example(node, label="ERROR"))
        elif bool(getattr(node, "is_missing", False)):
            missing_count += 1
            if len(error_examples) < 3:
                error_examples.append(_format_node_example(node, label="MISSING"))
        children = getattr(node, "children", None)
        if children:
            stack.extend(reversed(list(children)))

    if (
        not bool(getattr(root, "has_error", False))
        and error_count == 0
        and missing_count == 0
    ):
        return

    summary = (
        f"Tree-sitter parse validation failed for {language_name}: "
        f"errors={error_count}, missing={missing_count}"
    )
    if error_examples:
        summary = f"{summary}; examples={'; '.join(error_examples)}"
    raise ParseValidationError(summary)


def _format_node_example(node, *, label: str) -> str:
    start = getattr(node, "start_point", (0, 0))
    end = getattr(node, "end_point", (0, 0))
    return (
        f"{label}:{getattr(node, 'type', '?')}@"
        f"{int(start[0]) + 1}:{int(start[1]) + 1}-"
        f"{int(end[0]) + 1}:{int(end[1]) + 1}"
    )


__all__ = ["ParseValidationError", "validate_tree_or_raise"]
