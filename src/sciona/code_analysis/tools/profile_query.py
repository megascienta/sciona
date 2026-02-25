# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Tree-sitter query helpers for profile introspection."""

from __future__ import annotations

from functools import lru_cache

from tree_sitter_languages import get_language


def find_profile_nodes_of_types(
    node,
    *,
    language_name: str,
    node_types: tuple[str, ...],
    capture_name: str = "node",
) -> list[object]:
    if not node_types:
        return []
    query = _compile_query(language_name, tuple(sorted(node_types)), capture_name)
    captures = query.captures(node)
    found: list[object] = []
    seen: set[tuple[int, int, str]] = set()
    for captured_node, raw_name in captures:
        name = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else raw_name
        if name != capture_name:
            continue
        key = (captured_node.start_byte, captured_node.end_byte, captured_node.type)
        if key in seen:
            continue
        seen.add(key)
        found.append(captured_node)
    found.sort(key=lambda item: (item.start_byte, item.end_byte))
    return found


@lru_cache(maxsize=64)
def _compile_query(language_name: str, node_types: tuple[str, ...], capture_name: str):
    source = "\n".join(f"({node_type}) @{capture_name}" for node_type in node_types)
    language = get_language(language_name)
    if hasattr(language, "query"):
        return language.query(source)
    raise RuntimeError(
        f"Tree-sitter query API unavailable for profile language: {language_name}"
    )

