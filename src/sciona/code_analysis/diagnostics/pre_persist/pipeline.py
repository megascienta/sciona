# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diagnostic-only pre-persist classification pipeline."""

from __future__ import annotations

from typing import Sequence

from ...artifacts.call_resolution import (
    build_module_binding_index,
    build_module_context,
    build_symbol_index,
    build_typescript_barrel_export_map,
    resolve_callees,
)
from ...tools.call_extraction import CallExtractionRecord, PrePersistObservation
from ....data_storage.core_db import read_ops as core_read
from ....pipelines.exec.reporting_callsites import scope_bucket
from .classifier import classify_no_in_repo_candidate
from .models import DiagnosticAggregation, DiagnosticMissObservation
from .report import empty_diagnostic_buckets


def classify_pre_persist_misses(
    *,
    core_conn,
    snapshot_id: str,
    call_records: Sequence[CallExtractionRecord],
) -> dict[str, object]:
    if not call_records:
        return {
            "totals": empty_diagnostic_buckets(),
            "by_language": {},
            "by_scope": {
                "non_tests": empty_diagnostic_buckets(),
                "tests": empty_diagnostic_buckets(),
            },
            "observations": [],
        }
    symbol_index, _in_repo_callable_ids, callable_qname_by_id = build_symbol_index(
        core_conn, snapshot_id
    )
    (
        module_lookup,
        import_targets,
        expanded_import_targets,
        module_ancestors,
        module_file_by_name,
    ) = build_module_context(core_conn, snapshot_id)
    caller_metadata = core_read.caller_node_metadata_map(core_conn, snapshot_id)
    caller_language_map = core_read.caller_language_map(core_conn, snapshot_id)
    module_bindings_by_name = build_module_binding_index(
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
    )
    ts_barrel_export_map = build_typescript_barrel_export_map(
        import_targets=import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
    )
    aggregation = DiagnosticAggregation(
        totals=empty_diagnostic_buckets(),
        by_scope={
            "non_tests": empty_diagnostic_buckets(),
            "tests": empty_diagnostic_buckets(),
        },
    )
    for record in call_records:
        caller_id = record.caller_structural_id
        caller_module = module_lookup.get(caller_id)
        observations: list[PrePersistObservation] = []
        resolve_callees(
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
            pre_persist_observations=observations,
        )
        caller_info = caller_metadata.get(caller_id) or {}
        language = str(
            caller_info.get("language") or caller_language_map.get(caller_id) or "unknown"
        )
        file_path = str(caller_info.get("file_path") or "")
        scope_key = scope_bucket(file_path)
        for item in observations:
            observation = DiagnosticMissObservation(
                language=language,
                file_path=file_path,
                caller_structural_id=caller_id,
                caller_qualified_name=record.caller_qualified_name,
                caller_module=caller_module,
                identifier=item.identifier,
                ordinal=item.ordinal,
                callee_kind=item.callee_kind,
                candidate_module_hints=item.candidate_module_hints,
            )
            classified = classify_no_in_repo_candidate(observation)
            _inc_bucket(aggregation.totals, classified.bucket)
            language_buckets = aggregation.by_language.setdefault(
                language,
                empty_diagnostic_buckets(),
            )
            _inc_bucket(language_buckets, classified.bucket)
            _inc_bucket(aggregation.by_scope[scope_key], classified.bucket)
            aggregation.observations.append(
                {
                    "bucket": classified.bucket,
                    "reasons": list(classified.reasons),
                    "language": observation.language,
                    "file_path": observation.file_path,
                    "caller_structural_id": observation.caller_structural_id,
                    "caller_qualified_name": observation.caller_qualified_name,
                    "caller_module": observation.caller_module,
                    "identifier": observation.identifier,
                    "ordinal": observation.ordinal,
                    "callee_kind": observation.callee_kind,
                    "candidate_module_hints": list(observation.candidate_module_hints),
                    "scope": scope_key,
                }
            )
    return {
        "totals": aggregation.totals,
        "by_language": aggregation.by_language,
        "by_scope": aggregation.by_scope,
        "observations": aggregation.observations,
    }


def _inc_bucket(target: dict[str, int], bucket: str) -> None:
    target[bucket] = int(target.get(bucket, 0)) + 1
