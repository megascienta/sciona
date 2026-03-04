# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact graph/rollup derivation logic from code-analysis outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Sequence, cast

from ..analysis.graph import module_id_for
from ..contracts import select_strict_call_candidate
from ..config import CALLABLE_NODE_TYPES
from ..tools.call_extraction import CallExtractionRecord
from ...data_storage.artifact_db import rollup_persistence as artifact_persistence
from ...data_storage.core_db import read_ops as core_read


def rebuild_graph_rollups(
    artifact_conn,
    *,
    core_conn,
    snapshot_id: str,
) -> None:
    core_read.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    artifact_persistence.reset_graph_rollups(artifact_conn)
    node_rows = core_read.list_nodes_with_names(core_conn, snapshot_id)
    if not node_rows:
        return
    module_names = {
        qualified_name
        for _structural_id, node_type, qualified_name in node_rows
        if node_type == "module" and qualified_name
    }
    module_id_by_name = {
        qualified_name: structural_id
        for structural_id, node_type, qualified_name in node_rows
        if node_type == "module" and qualified_name
    }
    module_lookup: dict[str, str] = {}
    node_kind_lookup: dict[str, str] = {}
    for structural_id, node_type, qualified_name in node_rows:
        node_kind_lookup[structural_id] = node_type
        if qualified_name:
            module_name = module_id_for(qualified_name, module_names)
            module_structural_id = module_id_by_name.get(module_name)
            if module_structural_id:
                module_lookup[structural_id] = module_structural_id
    method_edges = core_read.list_edges_by_type(
        core_conn,
        snapshot_id,
        "LEXICALLY_CONTAINS",
    )
    node_type_by_id = {structural_id: node_type for structural_id, node_type, _q in node_rows}
    method_to_class = {
        dst_id: src_id
        for src_id, dst_id in method_edges
        if node_type_by_id.get(src_id) == "type" and node_type_by_id.get(dst_id) == "callable"
    }

    call_rows = artifact_persistence.list_call_edges(artifact_conn)
    module_calls: Counter[tuple[str, str]] = Counter()
    class_calls: Counter[tuple[str, str]] = Counter()
    for src_id, dst_id in call_rows:
        src_module = module_lookup.get(src_id)
        dst_module = module_lookup.get(dst_id)
        if src_module and dst_module:
            module_calls[(src_module, dst_module)] += 1
        src_class = method_to_class.get(src_id)
        dst_class = method_to_class.get(dst_id)
        if src_class and dst_class:
            class_calls[(src_class, dst_class)] += 1
    artifact_persistence.write_module_call_edges(
        artifact_conn,
        rows=[(src, dst, count) for (src, dst), count in module_calls.items()],
    )
    artifact_persistence.write_class_call_edges(
        artifact_conn,
        rows=[(src, dst, count) for (src, dst), count in class_calls.items()],
    )

    fan_in: dict[tuple[str, str], int] = defaultdict(int)
    fan_out: dict[tuple[str, str], int] = defaultdict(int)
    edge_rows = artifact_persistence.list_graph_edges(artifact_conn)
    for src_id, dst_id, edge_kind in edge_rows:
        fan_out[(src_id, edge_kind)] += 1
        fan_in[(dst_id, edge_kind)] += 1
    if fan_in or fan_out:
        all_keys = set(fan_in) | set(fan_out)
        stats_rows = []
        for node_id, edge_kind in sorted(all_keys):
            stats_rows.append(
                (
                    node_id,
                    node_kind_lookup.get(node_id, ""),
                    edge_kind,
                    fan_in.get((node_id, edge_kind), 0),
                    fan_out.get((node_id, edge_kind), 0),
                )
            )
        artifact_persistence.write_node_fan_stats(artifact_conn, rows=stats_rows)


def write_call_artifacts(
    *,
    artifact_conn,
    core_conn,
    snapshot_id: str,
    call_records: Sequence[CallExtractionRecord],
    eligible_callers: Iterable[str] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> None:
    """Write call artifacts for eligible callers."""
    core_read.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    if not call_records:
        return
    caller_set = (
        set(eligible_callers)
        if eligible_callers is not None
        else {record.caller_structural_id for record in call_records}
    )
    if not caller_set:
        return
    symbol_index = _build_symbol_index(core_conn, snapshot_id)
    module_lookup, import_targets = _build_module_context(core_conn, snapshot_id)
    node_hashes = _load_node_hashes(core_conn, snapshot_id, caller_set)
    processed_callers: set[str] = set()
    diagnostics_totals = _ensure_rollup_diagnostics(diagnostics)
    for record in call_records:
        caller_id = record.caller_structural_id
        if caller_id not in caller_set:
            continue
        caller_diag = _ensure_caller_diagnostics(diagnostics, record)
        caller_module_id = module_lookup.get(caller_id)
        callee_ids, _, resolution_stats, callsite_rows = _resolve_callees(
            record.callee_identifiers,
            symbol_index,
            caller_module_id=caller_module_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
        )
        artifact_persistence.upsert_call_sites(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id=caller_id,
            caller_qname=record.caller_qualified_name,
            caller_node_type=record.caller_node_type,
            rows=callsite_rows,
        )
        _merge_resolution_stats(caller_diag, diagnostics_totals, resolution_stats)
        if not callee_ids:
            _record_resolution_drop(
                caller_diag,
                diagnostics_totals,
                reason="no_resolved_callees",
            )
            continue
        if caller_id in processed_callers:
            _record_resolution_drop(
                caller_diag,
                diagnostics_totals,
                reason="duplicate_caller_record",
            )
            continue
        call_hash = node_hashes.get(caller_id)
        if not call_hash:
            _record_resolution_drop(
                caller_diag,
                diagnostics_totals,
                reason="missing_call_hash",
            )
            continue
        processed_callers.add(caller_id)
        artifact_persistence.upsert_node_calls(
            artifact_conn,
            caller_id=caller_id,
            callee_ids=sorted(callee_ids),
            call_hash=call_hash,
        )


def _build_symbol_index(core_conn, snapshot_id: str) -> dict[str, list[str]]:
    callable_types = sorted(CALLABLE_NODE_TYPES)
    rows = core_read.list_nodes_by_types(core_conn, snapshot_id, callable_types)
    index_sets: dict[str, set[str]] = defaultdict(set)
    for structural_id, _node_type, qualified_name in rows:
        if not qualified_name:
            continue
        terminal = _simple_identifier(qualified_name)
        if terminal:
            index_sets[terminal].add(structural_id)
        # Preserve fully-qualified call hints emitted by analyzers.
        index_sets[qualified_name].add(structural_id)
    return {key: sorted(values) for key, values in index_sets.items()}


def _build_module_context(
    core_conn,
    snapshot_id: str,
) -> tuple[dict[str, str], dict[str, set[str]]]:
    node_rows = core_read.list_nodes_with_names(core_conn, snapshot_id)
    module_names = {
        qualified_name
        for _structural_id, node_type, qualified_name in node_rows
        if node_type == "module" and qualified_name
    }
    module_id_by_name = {
        qualified_name: structural_id
        for structural_id, node_type, qualified_name in node_rows
        if node_type == "module" and qualified_name
    }
    module_lookup: dict[str, str] = {}
    for structural_id, _node_type, qualified_name in node_rows:
        if not qualified_name:
            continue
        module_name = module_id_for(qualified_name, module_names)
        module_structural_id = module_id_by_name.get(module_name)
        if module_structural_id:
            module_lookup[structural_id] = module_structural_id
    module_ids = set(module_id_by_name.values())
    import_targets: dict[str, set[str]] = defaultdict(set)
    for src_id, dst_id in core_read.list_edges_by_type(
        core_conn, snapshot_id, "IMPORTS_DECLARED"
    ):
        if src_id in module_ids and dst_id in module_ids:
            import_targets[src_id].add(dst_id)
    return module_lookup, import_targets


def _load_node_hashes(
    core_conn, snapshot_id: str, node_ids: Iterable[str]
) -> dict[str, str]:
    return core_read.node_hashes_for_ids(core_conn, snapshot_id, node_ids)


def _resolve_callees(
    identifiers: Sequence[str],
    symbol_index: dict[str, Sequence[str]],
    *,
    caller_module_id: str | None,
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
) -> tuple[
    set[str],
    set[str],
    dict[str, object],
    list[tuple[str, str, str | None, str | None, str | None, int, str, int | None, int | None, int]],
]:
    resolved_ids: set[str] = set()
    resolved_names: set[str] = set()
    callsite_rows: list[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
        ]
    ] = []
    ordinal_by_identifier: dict[str, int] = {}
    stats: dict[str, object] = {
        "identifiers_total": 0,
        "accepted_by_provenance": Counter(),
        "dropped_by_reason": Counter(),
        "candidate_count_histogram": Counter(),
    }
    for identifier in identifiers:
        stats["identifiers_total"] += 1
        direct_candidates = symbol_index.get(identifier) or []
        fallback_candidates = []
        if not direct_candidates and "." in identifier:
            fallback_candidates = symbol_index.get(identifier.rsplit(".", 1)[-1]) or []
        decision = select_strict_call_candidate(
            identifier=identifier,
            direct_candidates=direct_candidates,
            fallback_candidates=fallback_candidates,
            caller_module=caller_module_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
        )
        cast(Counter[int], stats["candidate_count_histogram"])[decision.candidate_count] += 1
        ordinal = ordinal_by_identifier.get(identifier, 0) + 1
        ordinal_by_identifier[identifier] = ordinal
        callee_kind = "qualified" if "." in identifier else "terminal"
        if decision.accepted_candidate:
            resolved_ids.add(decision.accepted_candidate)
            resolved_names.add(identifier)
            cast(Counter[str], stats["accepted_by_provenance"])[
                str(decision.accepted_provenance)
            ] += 1
            if decision.candidate_count > 0:
                callsite_rows.append(
                    (
                        identifier,
                        "accepted",
                        decision.accepted_candidate,
                        decision.accepted_provenance,
                        None,
                        decision.candidate_count,
                        callee_kind,
                        None,
                        None,
                        ordinal,
                    )
                )
            continue
        cast(Counter[str], stats["dropped_by_reason"])[str(decision.dropped_reason)] += 1
        if decision.candidate_count > 0:
            callsite_rows.append(
                (
                    identifier,
                    "dropped",
                    None,
                    None,
                    decision.dropped_reason,
                    decision.candidate_count,
                    callee_kind,
                    None,
                    None,
                    ordinal,
                )
            )
    return resolved_ids, resolved_names, stats, callsite_rows


def _ensure_rollup_diagnostics(diagnostics: dict[str, object] | None) -> dict[str, object]:
    if diagnostics is None:
        return {}
    diagnostics.setdefault("version", 1)
    diagnostics.setdefault("by_caller", {})
    totals = diagnostics.setdefault(
        "totals",
        {
            "identifiers_total": 0,
            "accepted_identifiers": 0,
            "dropped_identifiers": 0,
            "accepted_by_provenance": {},
            "dropped_by_reason": {},
            "candidate_count_histogram": {},
            "record_drops": {},
            "assembler_accepted_artifact_dropped": 0,
        },
    )
    return cast(dict[str, object], totals)


def _ensure_caller_diagnostics(
    diagnostics: dict[str, object] | None,
    record: CallExtractionRecord,
) -> dict[str, object]:
    if diagnostics is None:
        return {}
    by_caller = cast(dict[str, dict[str, object]], diagnostics.setdefault("by_caller", {}))
    entry = by_caller.setdefault(
        record.caller_structural_id,
        {
            "caller_qualified_name": record.caller_qualified_name,
            "caller_node_type": record.caller_node_type,
            "identifiers_total": 0,
            "accepted_identifiers": 0,
            "dropped_identifiers": 0,
            "accepted_by_provenance": {},
            "dropped_by_reason": {},
            "candidate_count_histogram": {},
            "record_drops": {},
            "assembler_accepted_artifact_dropped": 0,
        },
    )
    return entry


def _merge_resolution_stats(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    stats: dict[str, object],
) -> None:
    identifiers_total = int(stats.get("identifiers_total", 0))
    accepted = sum(cast(Counter[str], stats["accepted_by_provenance"]).values())
    dropped = sum(cast(Counter[str], stats["dropped_by_reason"]).values())
    _inc_scalar(caller_diag, "identifiers_total", identifiers_total)
    _inc_scalar(caller_diag, "accepted_identifiers", accepted)
    _inc_scalar(caller_diag, "dropped_identifiers", dropped)
    _inc_scalar(totals_diag, "identifiers_total", identifiers_total)
    _inc_scalar(totals_diag, "accepted_identifiers", accepted)
    _inc_scalar(totals_diag, "dropped_identifiers", dropped)
    _merge_counter_map(
        caller_diag, "accepted_by_provenance", stats["accepted_by_provenance"]
    )
    _merge_counter_map(
        caller_diag, "dropped_by_reason", stats["dropped_by_reason"]
    )
    _merge_counter_map(
        caller_diag, "candidate_count_histogram", stats["candidate_count_histogram"]
    )
    _merge_counter_map(
        totals_diag, "accepted_by_provenance", stats["accepted_by_provenance"]
    )
    _merge_counter_map(
        totals_diag, "dropped_by_reason", stats["dropped_by_reason"]
    )
    _merge_counter_map(
        totals_diag, "candidate_count_histogram", stats["candidate_count_histogram"]
    )


def _record_resolution_drop(
    caller_diag: dict[str, object],
    totals_diag: dict[str, object],
    *,
    reason: str,
) -> None:
    if caller_diag:
        _inc_map(caller_diag, "record_drops", reason)
        _inc_scalar(caller_diag, "assembler_accepted_artifact_dropped", 1)
    if totals_diag:
        _inc_map(totals_diag, "record_drops", reason)
        _inc_scalar(totals_diag, "assembler_accepted_artifact_dropped", 1)


def _merge_counter_map(
    target: dict[str, object],
    key: str,
    counter_values: object,
) -> None:
    if not target:
        return
    target_map = cast(dict[str, int], target.setdefault(key, {}))
    for bucket, count in cast(Counter[object], counter_values).items():
        if not count:
            continue
        bucket_key = str(bucket)
        target_map[bucket_key] = int(target_map.get(bucket_key, 0)) + int(count)


def _inc_scalar(target: dict[str, object], key: str, amount: int) -> None:
    if not target or not amount:
        return
    target[key] = int(target.get(key, 0)) + amount


def _inc_map(target: dict[str, object], key: str, bucket: str) -> None:
    if not target:
        return
    values = cast(dict[str, int], target.setdefault(key, {}))
    values[bucket] = int(values.get(bucket, 0)) + 1


def _simple_identifier(qualified_name: str) -> str | None:
    if not qualified_name:
        return None
    parts = qualified_name.rsplit(".", 1)
    return parts[-1] if parts else qualified_name


__all__ = ["rebuild_graph_rollups", "write_call_artifacts"]
