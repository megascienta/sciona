# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from tree_sitter import Parser
from tree_sitter_languages import get_language

from sciona.code_analysis.core.extract.languages.scope_resolver import ScopeResolver
from sciona.code_analysis.core.extract.utils import find_nodes_of_types_query


def _parser(language_name: str) -> Parser:
    parser = Parser()
    language = get_language(language_name)
    if hasattr(parser, "set_language"):
        parser.set_language(language)
    else:
        parser.language = language
    return parser


def test_scope_resolver_python_nested_lambda_maps_to_enclosing_method() -> None:
    source = b"""
class C:
    def run(self):
        fn = lambda: helper()
        fn()
"""
    root = _parser("python").parse(source).root_node
    method_node = find_nodes_of_types_query(
        root,
        language_name="python",
        node_types=("function_definition",),
    )[0]
    call_node = find_nodes_of_types_query(
        root,
        language_name="python",
        node_types=("call",),
    )[0]
    resolver = ScopeResolver(
        callable_qname_by_span={
            (method_node.start_byte, method_node.end_byte): "repo.mod.C.run"
        }
    )
    assert resolver.enclosing_callable(call_node) == "repo.mod.C.run"


def test_scope_resolver_returns_none_when_no_callable_ancestor() -> None:
    source = b"class C:\n    pass\n"
    root = _parser("python").parse(source).root_node
    class_node = find_nodes_of_types_query(
        root,
        language_name="python",
        node_types=("class_definition",),
    )[0]
    resolver = ScopeResolver(callable_qname_by_span={})
    assert resolver.enclosing_callable(class_node) is None
