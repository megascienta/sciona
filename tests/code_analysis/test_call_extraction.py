# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

import pytest
from tree_sitter import Parser
from tree_sitter_languages import get_language

from sciona.code_analysis.tools import call_extraction
from sciona.code_analysis.tools.call_extraction import (
    QualifiedCallIR,
    ReceiverCallIR,
    collect_call_targets,
)
from sciona.code_analysis.tools.call_extraction_targets import _normalize_callee_text


def _parser(language_name: str) -> Parser:
    parser = Parser()
    language = get_language(language_name)
    if hasattr(parser, "set_language"):
        parser.set_language(language)
    else:
        parser.language = language
    return parser


def test_collect_call_targets_normalizes_optional_chain() -> None:
    parser = _parser("typescript")
    source = b"""
class A {
  run() {
    this.service?.doWork();
  }
}
"""
    tree = parser.parse(source)
    root = tree.root_node
    targets = collect_call_targets(
        root,
        source,
        call_node_types={"call_expression"},
        skip_node_types=set(),
        query_language="typescript",
    )
    assert targets
    target = targets[0]
    assert target.callee_text == "this.service.doWork"
    assert target.receiver == "this"
    assert target.callee_kind == "receiver"
    assert isinstance(target.ir, ReceiverCallIR)
    assert target.ir.receiver_chain == ("this", "service")


def test_collect_call_targets_populates_qualified_ir() -> None:
    parser = _parser("python")
    source = b"""
def run():
    pkg.service.do_work()
"""
    tree = parser.parse(source)
    root = tree.root_node
    targets = collect_call_targets(
        root,
        source,
        call_node_types={"call"},
        skip_node_types=set(),
        query_language="python",
    )
    assert targets
    target = targets[0]
    assert isinstance(target.ir, QualifiedCallIR)
    assert target.ir.parts == ("pkg", "service", "do_work")


def test_collect_call_targets_query_mode_is_deterministic() -> None:
    parser = _parser("typescript")
    source = b"""
class A {
  run() {
    this.service?.doWork();
  }
}
"""
    tree = parser.parse(source)
    root = tree.root_node
    expected = collect_call_targets(
        root,
        source,
        call_node_types={"call_expression"},
        skip_node_types=set(),
        query_language="typescript",
    )
    actual = collect_call_targets(
        root,
        source,
        call_node_types={"call_expression"},
        skip_node_types=set(),
        query_language="typescript",
    )
    assert [(t.terminal, t.callee_text) for t in actual] == [
        (t.terminal, t.callee_text) for t in expected
    ]


def test_collect_call_targets_typescript_new_expression_support() -> None:
    parser = _parser("typescript")
    source = b"const value = new pkg.Service();"
    tree = parser.parse(source)
    root = tree.root_node
    targets = collect_call_targets(
        root,
        source,
        call_node_types={"new_expression"},
        skip_node_types=set(),
        callee_field_names=("constructor", "function", "type"),
        query_language="typescript",
    )
    assert targets
    assert targets[0].terminal == "Service"
    assert targets[0].callee_text == "pkg.Service"


def test_normalize_callee_text_is_language_aware() -> None:
    assert _normalize_callee_text("Foo::bar", language_name="python") == "Foo::bar"
    assert _normalize_callee_text("Foo::bar", language_name="java") == "Foo.bar"
    assert (
        _normalize_callee_text("this.service?.doWork", language_name="typescript")
        == "this.service.doWork"
    )


def test_call_query_compilation_fails_closed_when_query_api_unavailable(monkeypatch) -> None:
    class _NoQueryLanguage:
        pass

    monkeypatch.setattr(call_extraction, "get_language", lambda _name: _NoQueryLanguage())
    call_extraction._compile_call_query.cache_clear()
    with pytest.raises(RuntimeError, match="Tree-sitter query API unavailable"):
        call_extraction._compile_call_query("python", "(call) @call")


def test_terminal_identifier_query_surface_unknown_language_fails_closed() -> None:
    call_extraction._compile_terminal_identifier_query_for_language.cache_clear()
    with pytest.raises(RuntimeError, match="Terminal identifier query surface unavailable"):
        call_extraction._compile_terminal_identifier_query_for_language("go")
