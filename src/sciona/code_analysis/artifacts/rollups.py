# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact graph/rollup derivation logic from code-analysis outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from ..analysis.module_id import module_id_for
from ..tools.call_extraction import CallExtractionRecord
from ...data_storage.artifact_db.rollups import rollup_persistence as artifact_persistence
from ...data_storage.artifact_db.writes.write_callsite_pairs import build_site_hash
from ...data_storage.core_db import read_ops as core_read
from .call_resolution import (
    best_candidate_by_module_distance as _best_candidate_by_module_distance,
    best_candidate_by_module_path as _best_candidate_by_module_path,
    build_module_binding_index as _build_module_binding_index,
    build_module_context as _build_module_context,
    build_symbol_index as _build_symbol_index,
    build_typescript_barrel_export_map as _build_typescript_barrel_export_map,
    bounded_module_reachability as _bounded_module_reachability,
    callsite_pair_rows as _callsite_pair_rows,
    load_node_hashes as _load_node_hashes,
    module_distance as _module_distance,
    module_in_scope as _module_in_scope,
    module_qname_ancestors as _module_qname_ancestors,
    persisted_callsite_outcomes as _persisted_callsite_outcomes,
    resolve_callees as _resolve_callees,
    resolve_python_export_chain_ambiguous as _resolve_python_export_chain_ambiguous,
    resolve_typescript_barrel_ambiguous as _resolve_typescript_barrel_ambiguous,
    simple_identifier as _simple_identifier,
)
from .rollup_diagnostics import (
    ensure_caller_diagnostics as _ensure_caller_diagnostics,
    record_callsite_pair_expansion as _record_callsite_pair_expansion,
    ensure_rollup_diagnostics as _ensure_rollup_diagnostics,
    merge_resolution_stats as _merge_resolution_stats,
    record_callsite_flow as _record_callsite_flow,
    record_persisted_drop_observation as _record_persisted_drop_observation,
    record_pre_persist_filter_buckets as _record_pre_persist_filter_buckets,
    record_resolution_drop as _record_resolution_drop,
)


@dataclass(frozen=True)
class _PreparedCallArtifact:
    caller_id: str
    pair_write_rows: tuple[tuple[str, str, str, str], ...]
    pair_callee_ids: tuple[str, ...]
    call_hash: str
    write_node_calls: bool
    write_empty_node_calls: bool


def rebuild_graph_rollups(
    artifact_conn,
    *,
    core_conn,
    snapshot_id: str,
    progress_factory=None,
) -> None:
    core_read.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    progress = progress_factory("Rebuilding graph rollups", 4) if progress_factory else None
    artifact_persistence.reset_graph_rollups(artifact_conn)
    if progress:
        progress.advance(1)
    node_rows = core_read.list_nodes_with_names(core_conn, snapshot_id)
    if not node_rows:
        if progress:
            progress.close()
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
    module_lookup_rows: list[tuple[str, str]] = []
    for structural_id, node_type, qualified_name in node_rows:
        if qualified_name:
            module_name = module_id_for(qualified_name, module_names)
            module_structural_id = module_id_by_name.get(module_name)
            if module_structural_id:
                module_lookup_rows.append((structural_id, module_structural_id))
    method_edges = core_read.list_edges_by_type(
        core_conn,
        snapshot_id,
        "LEXICALLY_CONTAINS",
    )
    node_type_by_id = {structural_id: node_type for structural_id, node_type, _q in node_rows}
    method_to_class = {
        dst_id: src_id
        for src_id, dst_id in method_edges
        if node_type_by_id.get(src_id) == "classifier"
        and node_type_by_id.get(dst_id) == "callable"
    }

    artifact_persistence.reset_rollup_temp_tables(artifact_conn)
    try:
        artifact_persistence.load_module_lookup(artifact_conn, rows=module_lookup_rows)
        artifact_persistence.load_method_to_class(
            artifact_conn,
            rows=method_to_class.items(),
        )
        if progress:
            progress.advance(1)
        artifact_persistence.rebuild_module_call_edges(artifact_conn)
        artifact_persistence.rebuild_class_call_edges(artifact_conn)
        if progress:
            progress.advance(1)
        artifact_persistence.rebuild_node_fan_stats(artifact_conn)
        if progress:
            progress.advance(1)
    finally:
        artifact_persistence.reset_rollup_temp_tables(artifact_conn)
        if progress:
            progress.close()


def write_call_artifacts(
    *,
    artifact_conn,
    core_conn,
    snapshot_id: str,
    call_records: Sequence[CallExtractionRecord],
    eligible_callers: Iterable[str] | None = None,
    diagnostics: dict[str, object] | None = None,
    progress_factory=None,
) -> None:
    """Write persisted callsite pairs and derived call edges for eligible callers."""
    core_read.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    caller_set = (
        set(eligible_callers)
        if eligible_callers is not None
        else {record.caller_structural_id for record in call_records}
    )
    if not caller_set:
        return
    if not call_records:
        artifact_persistence.clear_call_artifacts_for_callers(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_ids=caller_set,
        )
        return
    duplicate_caller_ids = _duplicate_caller_ids(call_records, caller_set)
    if duplicate_caller_ids:
        joined = ", ".join(sorted(duplicate_caller_ids))
        raise ValueError(
            f"Duplicate call artifact records for caller ids: {joined}"
        )
    symbol_index, in_repo_callable_ids, callable_qname_by_id = _build_symbol_index(
        core_conn, snapshot_id
    )
    (
        module_lookup,
        import_targets,
        expanded_import_targets,
        module_ancestors,
        module_file_by_name,
    ) = _build_module_context(
        core_conn, snapshot_id
    )
    caller_language_map = core_read.caller_language_map(core_conn, snapshot_id)
    caller_metadata_map = core_read.caller_node_metadata_map(core_conn, snapshot_id)
    module_bindings_by_name = _build_module_binding_index(
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
    )
    ts_barrel_export_map = _build_typescript_barrel_export_map(
        import_targets=import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
    )
    node_hashes = _load_node_hashes(core_conn, snapshot_id, caller_set)
    processed_callers: set[str] = set()
    diagnostics_totals = _ensure_rollup_diagnostics(diagnostics)
    prepare_progress = (
        progress_factory("Preparing callsite pairs", len(call_records))
        if progress_factory and call_records
        else None
    )
    prepared_artifacts: list[_PreparedCallArtifact] = []
    for record in call_records:
        caller_id = record.caller_structural_id
        if caller_id not in caller_set:
            if prepare_progress:
                prepare_progress.advance(1)
            continue
        caller_diag = _ensure_caller_diagnostics(diagnostics, record)
        caller_module = module_lookup.get(caller_id)
        callee_ids, _, resolution_stats, callsite_rows = _resolve_callees(
            record.callee_identifiers,
            symbol_index,
            caller_module=caller_module,
            caller_language=caller_language_map.get(caller_id),
            module_lookup=module_lookup,
            callable_qname_by_id=callable_qname_by_id,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_ancestors=module_ancestors,
            module_bindings_by_name=module_bindings_by_name,
            module_file_by_name=module_file_by_name,
            ts_barrel_export_map=ts_barrel_export_map,
        )
        callee_ids, filtered_callsite_rows, filtered_out_buckets = _persisted_callsite_outcomes(
            callsite_rows,
            in_repo_callable_ids=in_repo_callable_ids,
        )
        pair_rows = _callsite_pair_rows(
            filtered_callsite_rows,
            in_repo_callable_ids=in_repo_callable_ids,
            symbol_index=symbol_index,
            caller_module=caller_module,
            caller_language=caller_language_map.get(caller_id),
            module_lookup=module_lookup,
            callable_qname_by_id=callable_qname_by_id,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_ancestors=module_ancestors,
        )
        pair_callee_ids = sorted({callee_id for _identifier, _ordinal, callee_id, _kind in pair_rows})
        strict_pre_persist_buckets = resolution_stats.get("pre_persist_buckets") or {}
        if isinstance(strict_pre_persist_buckets, dict):
            for bucket, count in strict_pre_persist_buckets.items():
                amount = int(count or 0)
                if amount <= 0:
                    continue
                filtered_out_buckets[str(bucket)] = (
                    int(filtered_out_buckets.get(str(bucket)) or 0) + amount
                )
        site_hash_by_key = {
            (str(row[0]), int(row[9])): _callsite_site_hash(
                snapshot_id=snapshot_id,
                caller_id=caller_id,
                row=row,
            )
            for row in filtered_callsite_rows
        }
        pair_count_by_site_hash = {
            site_hash: 0 for site_hash in site_hash_by_key.values()
        }
        pair_write_rows: list[tuple[str, str, str, str]] = []
        for identifier, call_ordinal, callee_id, pair_kind in pair_rows:
            site_hash = site_hash_by_key.get((str(identifier), int(call_ordinal)))
            if site_hash is None:
                continue
            pair_write_rows.append((identifier, site_hash, callee_id, pair_kind))
            pair_count_by_site_hash[site_hash] = pair_count_by_site_hash.get(site_hash, 0) + 1
        zero_pair_callsites = 0
        one_pair_callsites = 0
        multiple_pair_callsites = 0
        max_pairs_for_single_persisted_callsite = 0
        for pair_count in pair_count_by_site_hash.values():
            count = int(pair_count)
            max_pairs_for_single_persisted_callsite = max(
                max_pairs_for_single_persisted_callsite,
                count,
            )
            if count <= 0:
                zero_pair_callsites += 1
            elif count == 1:
                one_pair_callsites += 1
            else:
                multiple_pair_callsites += 1
        _record_callsite_pair_expansion(
            caller_diag,
            diagnostics_totals,
            persisted_callsites=len(filtered_callsite_rows),
            persisted_callsites_with_zero_pairs=zero_pair_callsites,
            persisted_callsites_with_one_pair=one_pair_callsites,
            persisted_callsites_with_multiple_pairs=multiple_pair_callsites,
            max_pairs_for_single_persisted_callsite=max_pairs_for_single_persisted_callsite,
        )
        accepted_rows = [
            row for row in filtered_callsite_rows if row[1] == "accepted" and row[2]
        ]
        dropped_rows = [row for row in filtered_callsite_rows if row[1] == "dropped"]
        caller_file_path = str(
            (caller_metadata_map.get(caller_id) or {}).get("file_path") or ""
        )
        caller_language = caller_language_map.get(caller_id)
        for dropped_row in dropped_rows:
            _record_persisted_drop_observation(
                diagnostics,
                caller_structural_id=caller_id,
                caller_qualified_name=record.caller_qualified_name,
                caller_module=caller_module,
                caller_language=caller_language,
                caller_file_path=caller_file_path,
                identifier=str(dropped_row[0]),
                ordinal=int(dropped_row[9]),
                drop_reason=str(dropped_row[4]) if dropped_row[4] is not None else None,
                candidate_count=int(dropped_row[5]),
                callee_kind=str(dropped_row[6]),
                in_scope_candidate_count=(
                    int(dropped_row[10]) if dropped_row[10] is not None else None
                ),
                candidate_module_hints=(
                    str(dropped_row[11]) if dropped_row[11] is not None else None
                ),
            )
        rescue_accepted = [
            row for row in accepted_rows if row[3] == "export_chain_narrowed"
        ]
        _record_pre_persist_filter_buckets(
            caller_diag,
            diagnostics_totals,
            buckets=filtered_out_buckets,
        )
        _record_callsite_flow(
            caller_diag,
            diagnostics_totals,
            observed_callsites=len(record.callee_identifiers),
            persisted_callsites=len(filtered_callsite_rows),
            finalized_accepted_callsites=len(accepted_rows),
            finalized_dropped_callsites=len(dropped_rows),
            rescue_accepted_callsites=len(rescue_accepted),
        )
        _merge_resolution_stats(caller_diag, diagnostics_totals, resolution_stats)
        if not pair_callee_ids:
            _record_resolution_drop(
                caller_diag,
                diagnostics_totals,
                reason="no_resolved_callees",
            )
            prepared_artifacts.append(
                _PreparedCallArtifact(
                    caller_id=caller_id,
                    pair_write_rows=tuple(pair_write_rows),
                    pair_callee_ids=(),
                    call_hash=node_hashes.get(caller_id, ""),
                    write_node_calls=False,
                    write_empty_node_calls=True,
                )
            )
            if prepare_progress:
                prepare_progress.advance(1)
            continue
        if caller_id in processed_callers:
            _record_resolution_drop(
                caller_diag,
                diagnostics_totals,
                reason="duplicate_caller_record",
            )
            if prepare_progress:
                prepare_progress.advance(1)
            continue
        call_hash = node_hashes.get(caller_id)
        if not call_hash:
            _record_resolution_drop(
                caller_diag,
                diagnostics_totals,
                reason="missing_call_hash",
            )
            prepared_artifacts.append(
                _PreparedCallArtifact(
                    caller_id=caller_id,
                    pair_write_rows=tuple(pair_write_rows),
                    pair_callee_ids=tuple(pair_callee_ids),
                    call_hash="",
                    write_node_calls=False,
                    write_empty_node_calls=False,
                )
            )
            if prepare_progress:
                prepare_progress.advance(1)
            continue
        processed_callers.add(caller_id)
        prepared_artifacts.append(
            _PreparedCallArtifact(
                caller_id=caller_id,
                pair_write_rows=tuple(pair_write_rows),
                pair_callee_ids=tuple(pair_callee_ids),
                call_hash=call_hash,
                write_node_calls=True,
                write_empty_node_calls=False,
            )
        )
        if prepare_progress:
            prepare_progress.advance(1)
    if prepare_progress:
        prepare_progress.close()

    write_progress = (
        progress_factory("Writing callsite pairs", len(prepared_artifacts))
        if progress_factory and prepared_artifacts
        else None
    )
    for prepared in prepared_artifacts:
        artifact_persistence.upsert_callsite_pairs(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id=prepared.caller_id,
            rows=list(prepared.pair_write_rows),
        )
        if prepared.write_empty_node_calls:
            artifact_persistence.upsert_node_calls(
                artifact_conn,
                caller_id=prepared.caller_id,
                callee_ids=(),
                call_hash=prepared.call_hash,
            )
        elif prepared.write_node_calls:
            artifact_persistence.upsert_node_calls(
                artifact_conn,
                caller_id=prepared.caller_id,
                callee_ids=list(prepared.pair_callee_ids),
                call_hash=prepared.call_hash,
            )
        if write_progress:
            write_progress.advance(1)
    if write_progress:
        write_progress.close()


__all__ = [
    "rebuild_graph_rollups",
    "write_call_artifacts",
    "_build_module_binding_index",
    "_build_module_context",
    "_build_symbol_index",
    "_build_typescript_barrel_export_map",
    "_module_distance",
    "_module_in_scope",
    "_module_qname_ancestors",
    "_persisted_callsite_outcomes",
    "_python_export_scope_modules",
    "_resolve_callees",
    "_resolve_python_export_chain_ambiguous",
    "_resolve_typescript_barrel_ambiguous",
    "_simple_identifier",
]


def _python_export_scope_modules(
    *,
    caller_module: str,
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_file_by_name: dict[str, str],
) -> set[str]:
    from .call_resolution_python import python_export_scope_modules

    return python_export_scope_modules(
        caller_module=caller_module,
        import_targets=import_targets,
        expanded_import_targets=expanded_import_targets,
        module_file_by_name=module_file_by_name,
        bounded_module_reachability=_bounded_module_reachability,
    )


def _duplicate_caller_ids(
    call_records: Sequence[CallExtractionRecord],
    caller_set: set[str],
) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in call_records:
        caller_id = record.caller_structural_id
        if caller_id not in caller_set:
            continue
        if caller_id in seen:
            duplicates.add(caller_id)
            continue
        seen.add(caller_id)
    return duplicates


def _build_typescript_barrel_export_map(
    *,
    import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
) -> dict[str, set[str]]:
    from .call_resolution_typescript import build_typescript_barrel_export_map

    return build_typescript_barrel_export_map(
        import_targets=import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
        bounded_module_reachability=_bounded_module_reachability,
    )


def _build_module_binding_index(
    *,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
) -> dict[str, set[str]]:
    from .call_resolution_python import build_module_binding_index

    return build_module_binding_index(
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
        simple_identifier=_simple_identifier,
    )


def _resolve_python_export_chain_ambiguous(
    *,
    identifier: str,
    direct_candidates: Sequence[str],
    fallback_candidates: Sequence[str],
    caller_module: str | None,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
) -> str | None:
    from .call_resolution_python import resolve_python_export_chain_ambiguous

    return resolve_python_export_chain_ambiguous(
        identifier=identifier,
        direct_candidates=direct_candidates,
        fallback_candidates=fallback_candidates,
        caller_module=caller_module,
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
        import_targets=import_targets,
        expanded_import_targets=expanded_import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
        simple_identifier=_simple_identifier,
        module_in_scope=_module_in_scope,
        best_candidate_by_module_path=_best_candidate_by_module_path,
        bounded_module_reachability=_bounded_module_reachability,
    )


def _resolve_typescript_barrel_ambiguous(
    *,
    identifier: str,
    direct_candidates: Sequence[str],
    fallback_candidates: Sequence[str],
    caller_module: str | None,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    ts_barrel_export_map: dict[str, set[str]],
) -> str | None:
    from .call_resolution_typescript import resolve_typescript_barrel_ambiguous

    return resolve_typescript_barrel_ambiguous(
        identifier=identifier,
        direct_candidates=direct_candidates,
        fallback_candidates=fallback_candidates,
        caller_module=caller_module,
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
        import_targets=import_targets,
        expanded_import_targets=expanded_import_targets,
        ts_barrel_export_map=ts_barrel_export_map,
        simple_identifier=_simple_identifier,
        module_in_scope=_module_in_scope,
        best_candidate_by_module_distance=_best_candidate_by_module_distance,
    )


def _callsite_site_hash(
    *,
    snapshot_id: str,
    caller_id: str,
    row: tuple[
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
        int | None,
        str | None,
    ],
) -> str:
    identifier = row[0]
    call_ordinal = row[9]
    return build_site_hash(
        snapshot_id=snapshot_id,
        caller_id=caller_id,
        identifier=identifier,
        call_ordinal=call_ordinal,
    )
