# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared analyzer helpers for call-target attribution."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Callable, Sequence

from ....tools.call_extraction import collect_call_targets
from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord
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


def emit_callable_import_edges(
    *,
    language: str,
    caller_qname: str,
    caller_node_type: str,
    resolved_identifiers: Sequence[str],
    import_modules: set[str],
    result,
) -> None:
    if not import_modules:
        return
    for identifier in resolved_identifiers:
        module_match = None
        for module in import_modules:
            if identifier == module or identifier.startswith(f"{module}."):
                if module_match is None or len(module) > len(module_match):
                    module_match = module
        if module_match is None:
            continue
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=caller_node_type,
                src_qualified_name=caller_qname,
                dst_language=language,
                dst_node_type="module",
                dst_qualified_name=module_match,
                edge_type="CALLABLE_IMPORTS_DECLARED",
            )
        )


def emit_unresolved_call_edges(
    *,
    language: str,
    module_name: str,
    caller_qname: str,
    caller_node_type: str,
    unresolved_candidates: Sequence[str],
    file_path,
    result,
) -> None:
    if not unresolved_candidates:
        return
    existing = {
        node.qualified_name for node in result.nodes if node.node_type == "unresolved_call_target"
    }
    for candidate in sorted({candidate.strip() for candidate in unresolved_candidates if candidate.strip()}):
        token = re.sub(r"[^A-Za-z0-9_]+", "_", candidate).strip("_") or "candidate"
        unresolved_qname = f"{module_name}.__unresolved__.{token}"
        if unresolved_qname not in existing:
            existing.add(unresolved_qname)
            result.nodes.append(
                SemanticNodeRecord(
                    language=language,
                    node_type="unresolved_call_target",
                    qualified_name=unresolved_qname,
                    display_name=candidate,
                    file_path=file_path,
                    start_line=1,
                    end_line=1,
                    start_byte=0,
                    end_byte=0,
                    metadata={"kind": "ambiguous_candidate"},
                )
            )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=caller_node_type,
                src_qualified_name=caller_qname,
                dst_language=language,
                dst_node_type="unresolved_call_target",
                dst_qualified_name=unresolved_qname,
                edge_type="UNRESOLVED_CALL",
                confidence=0.5,
            )
        )


__all__ = [
    "PendingCall",
    "assert_scope_resolver_parity",
    "collect_targets_by_callable",
    "emit_callable_import_edges",
    "emit_unresolved_call_edges",
    "emit_local_inheritance_edges",
    "scope_resolver_from_pending_calls",
]
