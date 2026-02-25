# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.utils import (
    count_lines,
    find_nodes_of_types_query,
)
from sciona.code_analysis.core.extract import utils as extract_utils
from sciona.code_analysis.tools.tree_sitter import build_parser
import pytest


def test_count_lines_counts_non_empty() -> None:
    assert count_lines(b"") == 1
    assert count_lines(b"a\n") == 1
    assert count_lines(b"a\nb") == 2


def test_find_nodes_of_types_query_returns_tree_sitter_nodes() -> None:
    source = b"def a():\n    pass\n"
    root = build_parser("python").parse(source).root_node
    nodes = find_nodes_of_types_query(
        root,
        language_name="python",
        node_types=("function_definition",),
    )
    assert len(nodes) == 1


def test_find_nodes_of_types_query_preserves_document_order() -> None:
    source = b"""
def a():
    pass

def b():
    pass

def c():
    pass
"""
    root = build_parser("python").parse(source).root_node
    nodes = find_nodes_of_types_query(
        root,
        language_name="python",
        node_types=("function_definition",),
    )
    names = []
    for node in nodes:
        name_node = node.child_by_field_name("name")
        assert name_node is not None
        names.append(source[name_node.start_byte : name_node.end_byte].decode("utf-8"))
    assert names == ["a", "b", "c"]


def test_compile_query_source_fails_closed_when_query_api_unavailable(monkeypatch) -> None:
    class _NoQueryLanguage:
        pass

    monkeypatch.setattr(extract_utils, "get_language", lambda _name: _NoQueryLanguage())
    extract_utils._compile_query_source.cache_clear()
    with pytest.raises(RuntimeError, match="Tree-sitter query API unavailable"):
        extract_utils._compile_query_source("python", "(function_definition) @node")
