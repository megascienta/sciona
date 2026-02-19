# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.analysis.orderings import order_edges, order_nodes, order_strings


def test_order_nodes_sorts_by_qualified_name() -> None:
    entries = [
        {"qualified_name": "pkg.beta"},
        {"qualified_name": "pkg.alpha"},
    ]
    order_nodes(entries)
    assert [entry["qualified_name"] for entry in entries] == [
        "pkg.alpha",
        "pkg.beta",
    ]


def test_order_edges_sorts_by_fields() -> None:
    entries = [
        {"src_structural_id": "b", "dst_structural_id": "a", "edge_type": "B"},
        {"src_structural_id": "a", "dst_structural_id": "b", "edge_type": "A"},
    ]
    order_edges(entries)
    assert entries[0]["src_structural_id"] == "a"


def test_order_strings_sorts_in_place() -> None:
    entries = ["b", "a"]
    order_strings(entries)
    assert entries == ["a", "b"]
