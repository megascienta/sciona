# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared helpers for language extractors."""

from __future__ import annotations

from pathlib import Path

from ....core.normalize_model import FileSnapshot


def repo_root_from_snapshot(snapshot: FileSnapshot) -> Path:
    rel_parts = snapshot.record.relative_path.parts
    if not rel_parts:
        return snapshot.record.path.parent
    return snapshot.record.path.parents[len(rel_parts) - 1]


def is_internal_module(module_name: str, module_index: set[str] | None) -> bool:
    if module_index is None:
        return False
    return module_name in module_index


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def leading_decorator_start_line(node, decorator_node_type: str = "decorator") -> int | None:
    """Return the 1-based line of the earliest contiguous preceding-sibling
    decorator/annotation node, or None if the node is not directly preceded
    by one."""
    parent = getattr(node, "parent", None)
    if parent is None:
        return None
    siblings = list(getattr(parent, "children", []) or [])
    try:
        index = siblings.index(node)
    except ValueError:
        return None
    earliest_line: int | None = None
    for sibling in reversed(siblings[:index]):
        if not getattr(sibling, "is_named", True):
            continue
        if getattr(sibling, "type", None) != decorator_node_type:
            break
        earliest_line = sibling.start_point[0] + 1
    return earliest_line


__all__ = [
    "is_internal_module",
    "leading_decorator_start_line",
    "node_text",
    "repo_root_from_snapshot",
]
