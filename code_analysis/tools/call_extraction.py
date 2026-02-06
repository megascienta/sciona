"""Call extraction helpers shared across core and artifact paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Set

from ..config import TERMINAL_IDENTIFIER_TYPES


@dataclass(frozen=True)
class CallExtractionRecord:
    """Call extraction metadata produced during ingestion."""

    caller_structural_id: str
    caller_qualified_name: str
    caller_node_type: str
    callee_identifiers: Sequence[str]


def collect_call_identifiers(
    node,
    content: bytes,
    *,
    call_node_types: Set[str],
    skip_node_types: Set[str],
    callee_field_names: Sequence[str] = ("function",),
) -> Sequence[str]:
    """Return stable list of call target identifiers found within the node."""

    identifiers: list[str] = []

    def walk(current) -> None:
        if current is None:
            return
        if current.type in skip_node_types:
            return
        if current.type in call_node_types:
            callee = None
            for field_name in callee_field_names:
                callee = current.child_by_field_name(field_name)
                if callee is not None:
                    break
            if callee is None:
                callee = _first_child(current)
            terminal = _terminal_identifier(callee, content)
            if terminal:
                identifiers.append(terminal)
        for child in getattr(current, "children", []):
            walk(child)

    walk(node)
    return tuple(dict.fromkeys(identifiers))


def _terminal_identifier(node, content: bytes) -> str | None:
    if node is None:
        return None
    result: str | None = None

    def walk(current) -> None:
        nonlocal result
        if current is None:
            return
        if current.type in TERMINAL_IDENTIFIER_TYPES:
            result = content[current.start_byte : current.end_byte].decode("utf-8")
        for child in getattr(current, "children", []):
            walk(child)

    walk(node)
    return result


def _first_child(node):
    children = getattr(node, "children", [])
    return children[0] if children else None
