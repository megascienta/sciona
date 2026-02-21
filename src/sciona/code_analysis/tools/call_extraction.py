# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Call extraction helpers shared across core and artifact paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence, Set

from ..config import TERMINAL_IDENTIFIER_TYPES


def normalize_call_identifiers(
    resolved_calls: Sequence[tuple[str, str, str, Sequence[str]]],
) -> list[tuple[str, str, str, list[str]]]:
    terminal_map_by_scope: dict[tuple[str, str], dict[str, str | None]] = {}
    for language, qualified, node_type, identifiers in resolved_calls:
        scope = _module_scope_for_call(qualified, node_type)
        bucket = terminal_map_by_scope.setdefault((language, scope), {})
        for identifier in identifiers:
            if "." not in identifier:
                continue
            terminal = identifier.rsplit(".", 1)[-1]
            existing = bucket.get(terminal)
            if existing is None and terminal in bucket:
                continue
            if existing is None:
                bucket[terminal] = identifier
            elif existing != identifier:
                bucket[terminal] = None
    normalized: list[tuple[str, str, str, list[str]]] = []
    for language, qualified, node_type, identifiers in resolved_calls:
        scope = _module_scope_for_call(qualified, node_type)
        terminal_map = terminal_map_by_scope.get((language, scope), {})
        updated: list[str] = []
        for identifier in identifiers:
            if "." in identifier:
                terminal = identifier.rsplit(".", 1)[-1]
                mapped = terminal_map.get(terminal)
                if mapped is None and terminal in terminal_map:
                    updated.append(terminal)
                elif mapped:
                    updated.append(mapped)
                else:
                    updated.append(identifier)
            else:
                mapped = terminal_map.get(identifier)
                if mapped:
                    updated.append(mapped)
                else:
                    updated.append(identifier)
        normalized.append((language, qualified, node_type, updated))
    return normalized


def _module_scope_for_call(qualified_name: str, node_type: str) -> str:
    parts = qualified_name.split(".")
    if node_type == "method":
        if len(parts) > 2:
            return ".".join(parts[:-2])
        return qualified_name
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return qualified_name


@dataclass(frozen=True)
class CallExtractionRecord:
    """Call extraction metadata produced during ingestion."""

    caller_structural_id: str
    caller_qualified_name: str
    caller_node_type: str
    callee_identifiers: Sequence[str]


@dataclass(frozen=True)
class CallTarget:
    """Captured call target text with terminal identifier."""

    terminal: str
    callee_text: str | None


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
    targets = collect_call_targets(
        node,
        content,
        call_node_types=call_node_types,
        skip_node_types=skip_node_types,
        callee_field_names=callee_field_names,
    )
    identifiers.extend(target.terminal for target in targets)
    return tuple(dict.fromkeys(identifiers))


def collect_call_targets(
    node,
    content: bytes,
    *,
    call_node_types: Set[str],
    skip_node_types: Set[str],
    callee_field_names: Sequence[str] = ("function",),
    callee_renderer: Callable[[object, object | None, bytes], str | None] | None = None,
) -> Sequence[CallTarget]:
    """Return stable list of call targets found within the node."""

    targets: list[CallTarget] = []

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
                if callee_renderer is not None:
                    callee_text = callee_renderer(current, callee, content)
                else:
                    callee_text = _callee_text(callee, content)
                targets.append(CallTarget(terminal=terminal, callee_text=callee_text))
        for child in getattr(current, "children", []):
            walk(child)

    walk(node)
    seen: set[tuple[str, str | None]] = set()
    ordered: list[CallTarget] = []
    for target in targets:
        key = (target.terminal, target.callee_text)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(target)
    return tuple(ordered)


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


def _callee_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _first_child(node):
    children = getattr(node, "children", [])
    return children[0] if children else None
