# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared tree-sitter parse validation helpers."""

from __future__ import annotations


class ParseValidationError(ValueError):
    """Raised when a parsed tree contains syntax error markers."""

    def __init__(self, message: str, *, diagnostics: dict[str, object]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


def collect_parse_validation_diagnostics(
    tree, *, language_name: str
) -> dict[str, object]:
    root = getattr(tree, "root_node", None)
    if root is None:
        return {
            "parse_validation_ok": False,
            "parse_error_nodes": 0,
            "parse_missing_nodes": 0,
            "parse_significant_missing_nodes": 0,
            "parse_examples": [],
            "parse_error_summary": (
                f"Tree-sitter parse validation failed for {language_name}: "
                "missing root node"
            ),
        }

    error_examples: list[str] = []
    error_count = 0
    missing_count = 0
    significant_missing_count = 0
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
            if node_type != "identifier":
                significant_missing_count += 1
            if len(error_examples) < 3:
                error_examples.append(_format_node_example(node, label="MISSING"))
        children = getattr(node, "children", None)
        if children:
            stack.extend(reversed(list(children)))

    summary = (
        f"Tree-sitter parse validation {'passed' if error_count == 0 and significant_missing_count == 0 else 'failed'} "
        f"for {language_name}: errors={error_count}, missing={missing_count}"
    )
    if error_examples:
        summary = f"{summary}; examples={'; '.join(error_examples)}"
    return {
        "parse_validation_ok": error_count == 0 and significant_missing_count == 0,
        "parse_error_nodes": error_count,
        "parse_missing_nodes": missing_count,
        "parse_significant_missing_nodes": significant_missing_count,
        "parse_examples": error_examples,
        "parse_error_summary": summary,
    }


def validate_tree_or_raise(tree, *, language_name: str) -> dict[str, object]:
    diagnostics = collect_parse_validation_diagnostics(tree, language_name=language_name)
    if bool(diagnostics.get("parse_validation_ok", False)):
        return diagnostics
    raise ParseValidationError(
        str(diagnostics.get("parse_error_summary", "Tree-sitter parse validation failed")),
        diagnostics=diagnostics,
    )


def _format_node_example(node, *, label: str) -> str:
    start = getattr(node, "start_point", (0, 0))
    end = getattr(node, "end_point", (0, 0))
    return (
        f"{label}:{getattr(node, 'type', '?')}@"
        f"{int(start[0]) + 1}:{int(start[1]) + 1}-"
        f"{int(end[0]) + 1}:{int(end[1]) + 1}"
    )


__all__ = [
    "ParseValidationError",
    "collect_parse_validation_diagnostics",
    "validate_tree_or_raise",
]
