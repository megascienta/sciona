# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Call extraction helpers shared across core and artifact paths."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Sequence, Set

from tree_sitter_languages import get_language

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
class TerminalCallIR:
    terminal: str


@dataclass(frozen=True)
class QualifiedCallIR:
    parts: tuple[str, ...]
    terminal: str


@dataclass(frozen=True)
class ReceiverCallIR:
    receiver_chain: tuple[str, ...]
    terminal: str


CallTargetIR = TerminalCallIR | QualifiedCallIR | ReceiverCallIR


@dataclass(frozen=True)
class CallTarget:
    """Captured call target text with terminal identifier."""

    terminal: str
    callee_text: str | None
    receiver: str | None = None
    receiver_chain: tuple[str, ...] = ()
    callee_kind: str = "unqualified"
    ir: CallTargetIR | None = None
    call_span: tuple[int, int] | None = None
    invocation_kind: str | None = None
    type_arguments: str | None = None


def collect_call_identifiers(
    node,
    content: bytes,
    *,
    call_node_types: Set[str],
    skip_node_types: Set[str],
    callee_field_names: Sequence[str] = ("function",),
    query_language: str,
) -> Sequence[str]:
    """Return stable list of call target identifiers found within the node."""

    identifiers: list[str] = []
    targets = collect_call_targets(
        node,
        content,
        call_node_types=call_node_types,
        skip_node_types=skip_node_types,
        callee_field_names=callee_field_names,
        query_language=query_language,
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
    query_language: str | None = None,
) -> Sequence[CallTarget]:
    """Return stable list of call targets found within the node."""
    if not query_language:
        raise RuntimeError("query_language is required for call extraction")
    return _collect_call_targets_query(
        node,
        content,
        call_node_types=call_node_types,
        skip_node_types=skip_node_types,
        callee_field_names=callee_field_names,
        callee_renderer=callee_renderer,
        query_language=query_language,
    )


def _terminal_identifier_query(node, content: bytes, *, query_language: str) -> str | None:
    if node is None or not query_language:
        return None
    query = _compile_terminal_identifier_query_for_language(query_language)
    captures = query.captures(node)
    candidates: list[object] = []
    seen: set[tuple[int, int, str]] = set()
    for captured_node, capture_name in captures:
        if isinstance(capture_name, bytes):
            capture_name = capture_name.decode("utf-8")
        if capture_name != "terminal":
            continue
        key = (captured_node.start_byte, captured_node.end_byte, captured_node.type)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(captured_node)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.start_byte, item.end_byte))
    terminal_node = candidates[-1]
    return content[terminal_node.start_byte : terminal_node.end_byte].decode("utf-8")


def _callee_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _normalize_callee_text(text: str | None) -> str | None:
    if not text:
        return text
    normalized = text.strip()
    normalized = normalized.replace("?.", ".")
    normalized = normalized.replace("!.", ".")
    normalized = normalized.replace("::", ".")
    return normalized


def _callee_shape(
    callee_text: str | None,
) -> tuple[str | None, tuple[str, ...], str]:
    if not callee_text or "." not in callee_text:
        return None, (), "unqualified"
    head = callee_text.rsplit(".", 1)[0].strip()
    chain = tuple(part for part in head.split(".") if part)
    if not chain:
        return None, (), "unqualified"
    kind = "member"
    if chain[0] in {"self", "cls", "this", "super"}:
        kind = "receiver"
    return chain[0], chain, kind


def _call_target_ir(
    terminal: str,
    callee_text: str | None,
    receiver_chain: tuple[str, ...],
    callee_kind: str,
) -> CallTargetIR:
    if not callee_text or "." not in callee_text:
        return TerminalCallIR(terminal=terminal)
    parts = tuple(part for part in callee_text.split(".") if part)
    if len(parts) < 2:
        return TerminalCallIR(terminal=terminal)
    if callee_kind == "receiver":
        return ReceiverCallIR(receiver_chain=receiver_chain, terminal=terminal)
    return QualifiedCallIR(parts=parts, terminal=terminal)


def _first_child(node):
    children = getattr(node, "children", [])
    return children[0] if children else None


def _collect_call_targets_query(
    node,
    content: bytes,
    *,
    call_node_types: Set[str],
    skip_node_types: Set[str],
    callee_field_names: Sequence[str],
    callee_renderer: Callable[[object, object | None, bytes], str | None] | None,
    query_language: str,
) -> tuple[CallTarget, ...]:
    call_nodes = _query_call_nodes(node, query_language, call_node_types)
    targets: list[CallTarget] = []
    for call_node in call_nodes:
        if _has_ancestor_in_set(call_node, node, skip_node_types):
            continue
        target = _call_target_from_call_node(
            call_node,
            content,
            callee_field_names=callee_field_names,
            callee_renderer=callee_renderer,
            query_language=query_language,
        )
        if target is not None:
            targets.append(target)
    return _dedupe_targets(targets)


def _query_call_nodes(node, query_language: str, call_node_types: Set[str]) -> list[object]:
    if not call_node_types:
        return []
    query = _compile_call_query_for_types(query_language, tuple(sorted(call_node_types)))
    captures = query.captures(node)
    nodes: list[object] = []
    seen: set[tuple[int, int, str]] = set()
    for capture in captures:
        captured_node, capture_name = capture
        if isinstance(capture_name, bytes):
            capture_name = capture_name.decode("utf-8")
        if capture_name != "call":
            continue
        key = (captured_node.start_byte, captured_node.end_byte, captured_node.type)
        if key in seen:
            continue
        seen.add(key)
        nodes.append(captured_node)
    nodes.sort(key=lambda item: (item.start_byte, item.end_byte))
    return nodes


@lru_cache(maxsize=32)
def _compile_call_query(language_name: str, source: str):
    language = get_language(language_name)
    if hasattr(language, "query"):
        return language.query(source)
    raise RuntimeError(f"Tree-sitter query API unavailable for language: {language_name}")


@lru_cache(maxsize=32)
def _call_query_source(call_node_types: tuple[str, ...]) -> str:
    return "\n".join(f"({node_type}) @call" for node_type in call_node_types)


@lru_cache(maxsize=64)
def _compile_call_query_for_types(language_name: str, call_node_types: tuple[str, ...]):
    source = _call_query_source(call_node_types)
    return _compile_call_query(language_name, source)


@lru_cache(maxsize=8)
def _compile_terminal_identifier_query_for_language(language_name: str):
    language = get_language(language_name)
    supported_node_types: list[str] = []
    for node_type in sorted(TERMINAL_IDENTIFIER_TYPES):
        try:
            language.query(f"({node_type}) @terminal")
        except Exception:
            continue
        supported_node_types.append(node_type)
    if not supported_node_types:
        raise RuntimeError(
            f"Tree-sitter terminal identifier query types unavailable for language: {language_name}"
        )
    source = "\n".join(f"({node_type}) @terminal" for node_type in supported_node_types)
    return _compile_call_query(language_name, source)


def _call_target_from_call_node(
    call_node,
    content: bytes,
    *,
    callee_field_names: Sequence[str],
    callee_renderer: Callable[[object, object | None, bytes], str | None] | None,
    query_language: str,
) -> CallTarget | None:
    callee = None
    for field_name in callee_field_names:
        callee = call_node.child_by_field_name(field_name)
        if callee is not None:
            break
    if callee is None:
        callee = _first_child(call_node)
    terminal = _terminal_identifier_query(callee, content, query_language=query_language)
    if not terminal:
        return None
    if callee_renderer is not None:
        callee_text = callee_renderer(call_node, callee, content)
    else:
        callee_text = _callee_text(callee, content)
    normalized_callee = _normalize_callee_text(callee_text)
    receiver, receiver_chain, callee_kind = _callee_shape(normalized_callee)
    ir = _call_target_ir(
        terminal,
        normalized_callee,
        receiver_chain,
        callee_kind,
    )
    type_arguments_node = call_node.child_by_field_name("type_arguments")
    type_arguments = _callee_text(type_arguments_node, content)
    return CallTarget(
        terminal=terminal,
        callee_text=normalized_callee,
        receiver=receiver,
        receiver_chain=receiver_chain,
        callee_kind=callee_kind,
        ir=ir,
        call_span=(call_node.start_byte, call_node.end_byte),
        invocation_kind=getattr(call_node, "type", None),
        type_arguments=type_arguments.strip() if type_arguments else None,
    )


def _dedupe_targets(targets: Sequence[CallTarget]) -> tuple[CallTarget, ...]:
    seen: set[tuple[str, str | None]] = set()
    ordered: list[CallTarget] = []
    for target in targets:
        key = (target.terminal, target.callee_text)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(target)
    return tuple(ordered)


def _has_ancestor_in_set(node, root, node_types: Set[str]) -> bool:
    root_span = (root.start_byte, root.end_byte, root.type)
    current = getattr(node, "parent", None)
    while current is not None:
        current_span = (current.start_byte, current.end_byte, current.type)
        if current_span == root_span:
            break
        if current.type in node_types:
            return True
        current = getattr(current, "parent", None)
    return False
