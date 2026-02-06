"""Shared extraction helpers."""

from __future__ import annotations

from typing import Iterator


def count_lines(content: bytes) -> int:
    if not content:
        return 1
    return content.count(b"\n") + (0 if content.endswith(b"\n") else 1)


def find_nodes_of_type(node, node_type: str) -> Iterator[object]:
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == node_type:
            yield current
        stack.extend(getattr(current, "children", []))
