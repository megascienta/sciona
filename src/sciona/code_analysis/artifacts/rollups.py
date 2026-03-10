# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact graph/rollup derivation logic from code-analysis outputs."""

from __future__ import annotations

from typing import Iterable, Sequence

from ..analysis.module_id import module_id_for
from ..tools.call_extraction import CallExtractionRecord
from ...data_storage.artifact_db.rollups import rollup_persistence as artifact_persistence
from ...data_storage.core_db import read_ops as core_read
from .call_resolution import (
    best_candidate_by_module_distance as _best_candidate_by_module_distance,
    best_candidate_by_module_path as _best_candidate_by_module_path,
    build_module_binding_index as _build_module_binding_index,
    build_module_context as _build_module_context,
    build_symbol_index as _build_symbol_index,
    build_typescript_barrel_export_map as _build_typescript_barrel_export_map,
    bounded_module_reachability as _bounded_module_reachability,
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
    ensure_rollup_diagnostics as _ensure_rollup_diagnostics,
    merge_resolution_stats as _merge_resolution_stats,
    record_callsite_flow as _record_callsite_flow,
    record_resolution_drop as _record_resolution_drop,
)


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
        artifact_persistence.rebuild_module_call_edges(artifact_conn)
        artifact_persistence.rebuild_class_call_edges(artifact_conn)
        artifact_persistence.rebuild_node_fan_stats(artifact_conn)
    finally:
        artifact_persistence.reset_rollup_temp_tables(artifact_conn)


def write_call_artifacts(
    *,
    artifact_conn,
    core_conn,
    snapshot_id: str,
    call_records: Sequence[CallExtractionRecord],
    eligible_callers: Iterable[str] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> None:
    """Write filtered artifact callsites and derived call edges for eligible callers.

    The persisted `call_sites` table is the artifact-layer working/reporting
    surface. It intentionally stores only the filtered in-scope candidate-bearing
    subset rather than the full observed callsite stream.
    """
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
    for record in call_records:
        caller_id = record.caller_structural_id
        if caller_id not in caller_set:
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
        _callee_ids, filtered_callsite_rows = _persisted_callsite_outcomes(
            callsite_rows,
            in_repo_callable_ids=in_repo_callable_ids,
        )
        artifact_persistence.upsert_call_sites(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id=caller_id,
            caller_qname=record.caller_qualified_name,
            caller_node_type=record.caller_node_type,
            rows=filtered_callsite_rows,
        )
        callee_ids = set(
            artifact_persistence.list_persisted_callsite_callees(
                artifact_conn,
                snapshot_id=snapshot_id,
                caller_id=caller_id,
            )
        )
        accepted_rows = [
            row for row in filtered_callsite_rows if row[1] == "accepted" and row[2]
        ]
        dropped_rows = [row for row in filtered_callsite_rows if row[1] == "dropped"]
        rescue_accepted = [
            row for row in accepted_rows if row[3] == "export_chain_narrowed"
        ]
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
