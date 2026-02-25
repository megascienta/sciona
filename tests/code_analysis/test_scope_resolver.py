# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.languages.scope_resolver import ScopeResolver
from sciona.code_analysis.core.extract.utils import find_nodes_of_type
from sciona.code_analysis.tools.tree_sitter import build_parser


def test_scope_resolver_python_nested_lambda_maps_to_enclosing_method() -> None:
    source = b"""
class C:
    def run(self):
        fn = lambda: helper()
        fn()
"""
    root = build_parser("python").parse(source).root_node
    method_node = next(find_nodes_of_type(root, "function_definition"))
    call_node = next(find_nodes_of_type(root, "call"))
    resolver = ScopeResolver(
        callable_qname_by_span={
            (method_node.start_byte, method_node.end_byte): "repo.mod.C.run"
        }
    )
    assert resolver.enclosing_callable(call_node) == "repo.mod.C.run"


def test_scope_resolver_returns_none_when_no_callable_ancestor() -> None:
    source = b"class C:\n    pass\n"
    root = build_parser("python").parse(source).root_node
    class_node = next(find_nodes_of_type(root, "class_definition"))
    resolver = ScopeResolver(callable_qname_by_span={})
    assert resolver.enclosing_callable(class_node) is None
