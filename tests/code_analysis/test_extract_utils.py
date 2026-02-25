# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.utils import count_lines, find_nodes_of_type


class _Node:
    def __init__(self, node_type: str, children=None):
        self.type = node_type
        self.children = children or []


def test_count_lines_counts_non_empty() -> None:
    assert count_lines(b"") == 1
    assert count_lines(b"a\n") == 1
    assert count_lines(b"a\nb") == 2


def test_find_nodes_of_type_walks_children() -> None:
    leaf = _Node("target")
    root = _Node("root", children=[_Node("other"), leaf])
    nodes = list(find_nodes_of_type(root, "target"))
    assert nodes == [leaf]


def test_find_nodes_of_type_preserves_document_order() -> None:
    first = _Node("target")
    second = _Node("target")
    third = _Node("target")
    root = _Node(
        "root",
        children=[
            _Node("wrapper", children=[first, second]),
            third,
        ],
    )
    nodes = list(find_nodes_of_type(root, "target"))
    assert nodes == [first, second, third]
