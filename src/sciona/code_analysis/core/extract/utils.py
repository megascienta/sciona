# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared extraction helpers."""

from __future__ import annotations

from functools import lru_cache

from tree_sitter_languages import get_language


def count_lines(content: bytes) -> int:
    if not content:
        return 1
    return content.count(b"\n") + (0 if content.endswith(b"\n") else 1)


def find_nodes_of_types_query(
    node,
    *,
    language_name: str,
    node_types: tuple[str, ...],
) -> list[object]:
    """Return document-ordered nodes for any of the requested types using Query API."""
    if not node_types:
        return []
    query = _compile_type_query(language_name, tuple(sorted(node_types)))
    captures = query.captures(node)
    results: list[object] = []
    seen: set[tuple[int, int, str]] = set()
    for captured_node, capture_name in captures:
        if isinstance(capture_name, bytes):
            capture_name = capture_name.decode("utf-8")
        if capture_name != "node":
            continue
        key = (captured_node.start_byte, captured_node.end_byte, captured_node.type)
        if key in seen:
            continue
        seen.add(key)
        results.append(captured_node)
    results.sort(key=lambda item: (item.start_byte, item.end_byte))
    return results


@lru_cache(maxsize=64)
def _compile_type_query(language_name: str, node_types: tuple[str, ...]):
    source = "\n".join(f"({node_type}) @node" for node_type in node_types)
    return _compile_query_source(language_name, source)


@lru_cache(maxsize=64)
def _compile_query_source(language_name: str, source: str):
    language = get_language(language_name)
    if hasattr(language, "query"):
        return language.query(source)
    raise RuntimeError(f"Tree-sitter query API unavailable for language: {language_name}")
