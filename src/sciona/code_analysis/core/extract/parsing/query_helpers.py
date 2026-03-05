# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Tree-sitter query and extraction helpers."""

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
    capture_name: str = "node",
) -> list[object]:
    """Return document-ordered nodes for any of the requested types using Query API."""
    if not node_types:
        return []
    expected_capture_name = capture_name
    query = _compile_type_query(
        language_name, tuple(sorted(node_types)), expected_capture_name
    )
    captures = query.captures(node)
    results: list[object] = []
    seen: set[tuple[int, int, str]] = set()
    for captured_node, raw_capture_name in captures:
        resolved_name = (
            raw_capture_name.decode("utf-8")
            if isinstance(raw_capture_name, bytes)
            else raw_capture_name
        )
        if resolved_name != expected_capture_name:
            continue
        key = (captured_node.start_byte, captured_node.end_byte, captured_node.type)
        if key in seen:
            continue
        seen.add(key)
        results.append(captured_node)
    results.sort(key=lambda item: (item.start_byte, item.end_byte))
    return results


@lru_cache(maxsize=64)
def _compile_type_query(
    language_name: str, node_types: tuple[str, ...], capture_name: str = "node"
):
    source = "\n".join(f"({node_type}) @{capture_name}" for node_type in node_types)
    return _compile_query_source(language_name, source)


@lru_cache(maxsize=64)
def _compile_query_source(language_name: str, source: str):
    signature = _language_signature(language_name)
    return _compile_query_source_cached(language_name, signature, source)


@lru_cache(maxsize=64)
def _compile_query_source_cached(language_name: str, signature: str, source: str):
    # `signature` is intentionally part of the cache key so grammar upgrades
    # invalidate stale compiled queries even when the language name is unchanged.
    del signature
    language = get_language(language_name)
    if hasattr(language, "query"):
        return language.query(source)
    raise RuntimeError(f"Tree-sitter query API unavailable for language: {language_name}")


def _language_signature(language_name: str) -> str:
    language = get_language(language_name)
    version = getattr(language, "version", None)
    abi_version = getattr(language, "abi_version", None)
    return f"{type(language).__name__}:{version}:{abi_version}"


def find_direct_children_query(node, *, language_name: str) -> list[object]:
    """Return direct named child nodes using tree-sitter field API."""
    _ = language_name
    direct = list(getattr(node, "named_children", []))
    direct.sort(key=lambda item: (item.start_byte, item.end_byte))
    return direct


__all__ = [
    "count_lines",
    "find_nodes_of_types_query",
    "find_direct_children_query",
    "_compile_type_query",
    "_compile_query_source",
]
