# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared analyzer helpers for call-target attribution."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ....tools.call_extraction import collect_call_targets
from ...normalize.model import EdgeRecord, FileSnapshot
from .scope_resolver import ScopeResolver


PendingCall = tuple[str, str, object | None, str | None]


def scope_resolver_from_pending_calls(
    pending_calls: list[PendingCall],
) -> ScopeResolver:
    spans: dict[tuple[int, int], str] = {}
    for qualified, _node_type, body_node, _class_name in pending_calls:
        callable_node = getattr(body_node, "parent", None)
        if callable_node is None:
            continue
        spans[(callable_node.start_byte, callable_node.end_byte)] = qualified
    return ScopeResolver(callable_qname_by_span=spans)


def assert_scope_resolver_parity(
    *,
    pending_callables: set[str],
    call_targets_by_callable: dict[str, tuple[object, ...]],
) -> None:
    unknown = set(call_targets_by_callable) - pending_callables
    if unknown:
        raise RuntimeError(f"scope resolver mismatch: unknown callables {sorted(unknown)}")


def collect_targets_by_callable(
    *,
    scope_resolver: ScopeResolver,
    pending_calls: list[PendingCall],
    snapshot: FileSnapshot,
    language: str,
    call_node_types: set[str],
    skip_node_types: set[str],
    callee_field_names: tuple[str, ...] = ("function",),
    callee_renderer: Callable[[object, object, bytes], str | None] | None = None,
) -> dict[str, tuple[object, ...]]:
    grouped: dict[str, list[object]] = defaultdict(list)
    for _qualified, _node_type, body_node, _class_name in pending_calls:
        if body_node is None:
            continue
        call_targets = collect_call_targets(
            body_node,
            snapshot.content,
            call_node_types=call_node_types,
            skip_node_types=skip_node_types,
            callee_field_names=callee_field_names,
            callee_renderer=callee_renderer,
            query_language=language,
        )
        for target in call_targets:
            if target.call_span is None:
                continue
            caller = scope_resolver.enclosing_callable_for_span(
                root=body_node,
                call_span=target.call_span,
            )
            if caller is None:
                continue
            grouped[caller].append(target)
    return {qualified: tuple(targets) for qualified, targets in grouped.items()}


def emit_local_inheritance_edges(*, language: str, result) -> None:
    class_nodes = [node for node in result.nodes if node.node_type == "class"]
    class_qnames_by_simple: dict[str, set[str]] = {}
    kind_by_qname: dict[str, str] = {}
    for node in class_nodes:
        class_qnames_by_simple.setdefault(node.display_name, set()).add(node.qualified_name)
        kind_by_qname[node.qualified_name] = ((node.metadata or {}).get("kind") or "class")
    for node in class_nodes:
        metadata = node.metadata or {}
        bases = metadata.get("bases")
        if not isinstance(bases, list):
            continue
        for base in bases:
            if not isinstance(base, str):
                continue
            simple = base.split(".")[-1].strip()
            if not simple:
                continue
            candidates = class_qnames_by_simple.get(simple, set())
            if len(candidates) != 1:
                continue
            target_qname = next(iter(candidates))
            src_kind = (metadata.get("kind") or "class")
            dst_kind = kind_by_qname.get(target_qname, "class")
            edge_type = (
                "IMPLEMENTS"
                if src_kind in {"class", "record"} and dst_kind == "interface"
                else "EXTENDS"
            )
            result.edges.append(
                EdgeRecord(
                    src_language=language,
                    src_node_type="class",
                    src_qualified_name=node.qualified_name,
                    dst_language=language,
                    dst_node_type="class",
                    dst_qualified_name=target_qname,
                    edge_type=edge_type,
                )
            )


__all__ = [
    "PendingCall",
    "assert_scope_resolver_parity",
    "collect_targets_by_callable",
    "emit_local_inheritance_edges",
    "scope_resolver_from_pending_calls",
]
