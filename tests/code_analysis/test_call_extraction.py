# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.tools.call_extraction import (
    QualifiedCallIR,
    ReceiverCallIR,
    collect_call_targets,
)
from sciona.code_analysis.tools.tree_sitter import build_parser


def test_collect_call_targets_normalizes_optional_chain() -> None:
    parser = build_parser("typescript")
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
    parser = build_parser("python")
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
    parser = build_parser("typescript")
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
