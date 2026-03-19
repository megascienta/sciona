# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from tree_sitter import Parser

from sciona.code_analysis.core.extract.parsing.parser_bootstrap import (
    bootstrap_tree_sitter_parser,
)
from sciona.code_analysis.core.extract.parsing.parse_validation import (
    ParseValidationError,
    collect_parse_validation_diagnostics,
    validate_tree_or_raise,
)
from sciona.code_analysis.core.extract.parsing.query_helpers import (
    count_lines,
    find_direct_children_of_types_query,
    find_direct_children_query,
    find_nodes_of_types_query,
)
from sciona.code_analysis.core.extract.parsing import query_helpers as extract_utils
import pytest


def _parser(language_name: str) -> Parser:
    parser, _language, _diagnostics = bootstrap_tree_sitter_parser(language_name)
    return parser


def test_bootstrap_tree_sitter_parser_returns_diagnostics() -> None:
    parser, language, diagnostics = bootstrap_tree_sitter_parser("python")
    assert isinstance(parser, Parser)
    assert language is not None
    assert diagnostics["language_name"] == "python"
    assert diagnostics["binding_api"] in {"set_language", "language_attr"}
    assert diagnostics["query_api_available"] is True
    assert diagnostics["parser_class"] == "Parser"
    assert diagnostics["language_class"]
    assert diagnostics["language_module"]


def test_bootstrap_diagnostics_are_stable_across_calls() -> None:
    _p1, _l1, d1 = bootstrap_tree_sitter_parser("python")
    _p2, _l2, d2 = bootstrap_tree_sitter_parser("python")
    stable_keys = {
        "language_name",
        "binding_api",
        "query_api_available",
        "parser_class",
        "language_class",
        "language_module",
        "language_version",
        "language_abi_version",
    }
    assert {key: d1.get(key) for key in stable_keys} == {
        key: d2.get(key) for key in stable_keys
    }


def test_count_lines_counts_non_empty() -> None:
    assert count_lines(b"") == 1
    assert count_lines(b"a\n") == 1
    assert count_lines(b"a\nb") == 2


def test_find_nodes_of_types_query_returns_tree_sitter_nodes() -> None:
    source = b"def a():\n    pass\n"
    root = _parser("python").parse(source).root_node
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
    root = _parser("python").parse(source).root_node
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


def test_find_direct_children_query_returns_direct_nodes_only() -> None:
    source = b"""
class A:
    def run(self):
        pass
"""
    root = _parser("python").parse(source).root_node
    children = find_direct_children_query(root, language_name="python")
    assert children
    assert any(child.type == "class_definition" for child in children)


def test_find_direct_children_of_types_query_filters_to_direct_matches() -> None:
    source = b"""
def outer():
    if True:
        def inner():
            pass
"""
    root = _parser("python").parse(source).root_node
    children = find_direct_children_of_types_query(
        root,
        language_name="python",
        node_types=("function_definition",),
    )
    assert [child.type for child in children] == ["function_definition"]


def test_compile_query_source_fails_closed_when_query_api_unavailable(monkeypatch) -> None:
    class _NoQueryLanguage:
        pass

    monkeypatch.setattr(extract_utils, "get_language", lambda _name: _NoQueryLanguage())
    extract_utils._compile_query_source.cache_clear()
    with pytest.raises(RuntimeError, match="Tree-sitter query API unavailable"):
        extract_utils._compile_query_source("python", "(function_definition) @node")


def test_parse_validation_treats_missing_identifier_as_non_significant() -> None:
    class _Node:
        def __init__(self, node_type: str, *, is_missing: bool = False, children=None):
            self.type = node_type
            self.is_missing = is_missing
            self.children = list(children or [])
            self.start_point = (0, 0)
            self.end_point = (0, 0)

    class _Tree:
        def __init__(self, root):
            self.root_node = root

    tree = _Tree(_Node("module", children=[_Node("identifier", is_missing=True)]))
    diagnostics = collect_parse_validation_diagnostics(tree, language_name="python")

    assert diagnostics["parse_validation_ok"] is True
    assert diagnostics["parse_missing_nodes"] == 1
    assert diagnostics["parse_significant_missing_nodes"] == 0


def test_validate_tree_or_raise_raises_on_significant_missing_node() -> None:
    class _Node:
        def __init__(self, node_type: str, *, is_missing: bool = False, children=None):
            self.type = node_type
            self.is_missing = is_missing
            self.children = list(children or [])
            self.start_point = (0, 0)
            self.end_point = (0, 0)

    class _Tree:
        def __init__(self, root):
            self.root_node = root

    tree = _Tree(_Node("module", children=[_Node("parameters", is_missing=True)]))

    with pytest.raises(ParseValidationError):
        validate_tree_or_raise(tree, language_name="python")
