# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.tools.call_extraction import collect_call_targets
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
    )
    assert targets
    target = targets[0]
    assert target.callee_text == "this.service.doWork"
    assert target.receiver == "this"
    assert target.callee_kind == "receiver"
