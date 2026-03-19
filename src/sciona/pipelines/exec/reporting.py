# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""DB-backed snapshot reporting for CLI summaries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import sqlite3

from ..domain.repository import RepoState
from ...data_storage.connections import artifact_readonly, core_readonly
from ...data_storage.core_db import read_ops as core_read
from ...data_storage.artifact_db.reporting import read_reporting as artifact_reporting
from ...data_storage.artifact_db.reporting import read_status as artifact_status
from .reporting_callsites import (
    filtered_pre_persist_buckets_payload as _filtered_pre_persist_buckets_payload_impl,
    scope_bucket as _scope_bucket_impl,
)


@dataclass(frozen=True)
class LanguageMetrics:
    language: str
    files: int = 0
    nodes: int = 0
    edges: int | None = None
    persisted_in_scope_pairs: int | None = None
    finalized_call_edges: int | None = None
    observed_syntactic_callsites: int | None = None
    filtered_pre_persist: int | None = None
    persisted_callsites: int | None = None
    persisted_accepted: int | None = None
    persisted_dropped: int | None = None
    filtered_pre_persist_buckets: dict[str, int] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            self.language: {
                "structure": {
                    "files": self.files,
                    "nodes": self.nodes,
                    "edges": self.edges,
                },
                "callsites": {
                    "observed_syntactic_callsites": self.observed_syntactic_callsites,
                    "filtered_pre_persist": self.filtered_pre_persist,
                    "persisted_callsites": self.persisted_callsites,
                    "persisted_accepted": self.persisted_accepted,
                    "persisted_dropped": self.persisted_dropped,
                },
                "pre_persist_filter": _filtered_pre_persist_buckets_payload(
                    self.filtered_pre_persist_buckets
                ),
                "call_materialization": {
                    "callsite_pairs": self.persisted_in_scope_pairs,
                    "finalized_call_edges": self.finalized_call_edges,
                },
            }
        }


SECTION_LABELS = {
    "structure": "Structure",
    "callsites": "Callsites",
    "pre_persist_filter": "Pre-Persist Filter",
    "call_materialization": "Call Materialization",
    "timing": "Timing",
}

FIELD_LABELS = {
    "files": "Files",
    "nodes": "Nodes",
    "edges": "Edges",
    "observed_syntactic_callsites": "Observed Syntactic Callsites",
    "filtered_pre_persist": "Filtered Pre-Persist",
    "persisted_callsites": "Persisted Callsites",
    "persisted_accepted": "Persisted Accepted",
    "persisted_dropped": "Persisted Dropped",
    "out_of_scope_call": "Out-Of-Scope Call",
    "weak_static_evidence": "Weak Static Evidence",
    "structural_gap": "Structural Gap",
    "unclassified": "Unclassified",
    "callsite_pairs": "Callsite Pairs",
    "finalized_call_edges": "Finalized Call Edges",
    "build_total_seconds": "Build Total Time",
    "build_wall_seconds": "Build Wall Time",
    "build_phase_timings": "Build Phase Timing",
}

SCOPE_LABELS = {
    "non_tests": "Non-Tests",
    "tests": "Tests",
}

PHASE_LABELS = {
    "compute_build_fingerprint": "Compute Build Fingerprint",
    "discover_files": "Discover Files",
    "prepare_snapshots": "Prepare Snapshots",
    "register_modules": "Register Modules",
    "build_structural_index": "Build Structural Index",
    "derive_call_artifacts": "Extract Call Observations",
    "prepare_callsite_pairs": "Prepare Callsite Pairs",
    "write_callsite_pairs": "Write Callsite Pairs",
    "rebuild_graph_index": "Rebuild Call Graph Index",
    "rebuild_graph_rollups": "Rebuild Graph Rollups",
}


def _labels_payload() -> dict[str, object]:
    return {
        "sections": dict(SECTION_LABELS),
        "fields": dict(FIELD_LABELS),
        "scopes": dict(SCOPE_LABELS),
        "phases": dict(PHASE_LABELS),
    }


def snapshot_report(
    repo_state: RepoState,
    *,
    snapshot_id: str,
    include_failure_reasons: bool = False,
) -> dict[str, object] | None:
    del include_failure_reasons
    language_metrics: dict[str, LanguageMetrics] = {}
    caller_language: dict[str, str] = {}
    caller_metadata: dict[str, dict[str, object]] = {}
    file_node_distribution_by_language: dict[str, list[tuple[str, int]]] = {}
    created_at: str | None = None
    build_total_seconds: float | None = None
    build_wall_seconds: float | None = None
    build_phase_timings: dict[str, float] | None = None
    call_resolution_diagnostics: dict[str, object] | None = None

    with core_readonly(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        created_at = core_read.snapshot_created_at(conn, snapshot_id)
        if created_at is None:
            return None
        files_and_nodes = core_read.language_file_node_counts(conn, snapshot_id)
        for item in files_and_nodes:
            language = str(item["language"])
            language_metrics[language] = LanguageMetrics(
                language=language,
                files=int(item["file_count"] or 0),
                nodes=int(item["node_count"] or 0),
            )
        caller_metadata = core_read.caller_node_metadata_map(conn, snapshot_id)
        caller_language = {
            structural_id: str(meta["language"])
            for structural_id, meta in caller_metadata.items()
        }
        file_node_distribution = core_read.language_file_node_distribution(conn, snapshot_id)
        for item in file_node_distribution:
            language = str(item.get("language") or "")
            file_path = str(item.get("file_path") or "")
            node_count = int(item.get("node_count") or 0)
            if not language or not file_path:
                continue
            file_node_distribution_by_language.setdefault(language, []).append(
                (file_path, node_count)
            )

    artifact_available = False
    pair_totals: dict[str, int] = defaultdict(int)
    pair_scope_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"non_tests": 0, "tests": 0}
    )
    graph_edge_totals: dict[str, int] = defaultdict(int)
    graph_edge_scope_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"non_tests": 0, "tests": 0}
    )
    call_edge_totals: dict[str, int] = defaultdict(int)
    call_edge_scope_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"non_tests": 0, "tests": 0}
    )

    try:
        with artifact_readonly(
            repo_state.artifact_db_path, repo_root=repo_state.repo_root
        ) as conn:
            artifact_available = True
            build_total_seconds = artifact_status.build_total_seconds_for_snapshot(
                conn, snapshot_id=snapshot_id
            )
            build_wall_seconds = artifact_status.build_wall_seconds_for_snapshot(
                conn, snapshot_id=snapshot_id
            )
            build_phase_timings = artifact_status.build_phase_timings_for_snapshot(
                conn, snapshot_id=snapshot_id
            )
            call_resolution_diagnostics = (
                artifact_status.call_resolution_diagnostics_for_snapshot(
                    conn, snapshot_id=snapshot_id
                )
            )
            for item in artifact_reporting.callsite_pair_caller_counts(
                conn, snapshot_id=snapshot_id
            ):
                caller_id = str(item["caller_id"])
                language = caller_language.get(caller_id)
                if not language:
                    continue
                caller_info = caller_metadata.get(caller_id) or {}
                scope_key = _scope_bucket(str(caller_info.get("file_path") or ""))
                count = int(item["pair_count"] or 0)
                pair_totals[language] += count
                pair_scope_totals[language][scope_key] += count
            for item in artifact_reporting.graph_edge_source_counts(conn):
                source_id = str(item["src_node_id"])
                source_info = caller_metadata.get(source_id) or {}
                language = str(source_info.get("language") or "").strip()
                file_path = str(source_info.get("file_path") or "")
                if not language or not file_path:
                    continue
                scope_key = _scope_bucket(file_path)
                count = int(item["edge_count"] or 0)
                graph_edge_totals[language] += count
                graph_edge_scope_totals[language][scope_key] += count
            for item in artifact_reporting.node_call_caller_counts(conn):
                caller_id = str(item["caller_id"])
                language = caller_language.get(caller_id)
                if not language:
                    continue
                caller_info = caller_metadata.get(caller_id) or {}
                scope_key = _scope_bucket(str(caller_info.get("file_path") or ""))
                count = int(item["edge_count"] or 0)
                call_edge_totals[language] += count
                call_edge_scope_totals[language][scope_key] += count
    except sqlite3.Error:
        artifact_available = False

    diagnostics_by_language: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "observed_syntactic_callsites": 0,
            "filtered_pre_persist": 0,
            "persisted_callsites": 0,
            "persisted_accepted": 0,
            "persisted_dropped": 0,
        }
    )
    diagnostics_record_drops_by_language: dict[str, dict[str, int]] = defaultdict(dict)
    diagnostics_pre_persist_buckets_by_language: dict[str, dict[str, int]] = defaultdict(dict)
    diagnostics_pair_expansion_by_language: dict[str, dict[str, int]] = defaultdict(dict)
    diagnostics_by_scope: dict[str, dict[str, dict[str, int | dict[str, int]]]] = defaultdict(
        lambda: {
            "non_tests": {
                "observed_syntactic_callsites": 0,
                "filtered_pre_persist": 0,
                "persisted_callsites": 0,
                "persisted_accepted": 0,
                "persisted_dropped": 0,
                "record_drops": {},
                "filtered_pre_persist_buckets": {},
                "persisted_callsite_pair_expansion": {},
            },
            "tests": {
                "observed_syntactic_callsites": 0,
                "filtered_pre_persist": 0,
                "persisted_callsites": 0,
                "persisted_accepted": 0,
                "persisted_dropped": 0,
                "record_drops": {},
                "filtered_pre_persist_buckets": {},
                "persisted_callsite_pair_expansion": {},
            },
        }
    )
    diagnostics_totals = {
        "observed_syntactic_callsites": 0,
        "filtered_pre_persist": 0,
        "persisted_callsites": 0,
        "persisted_accepted": 0,
        "persisted_dropped": 0,
    }
    diagnostics_total_record_drops: dict[str, int] = {}
    diagnostics_total_pre_persist_buckets: dict[str, int] = {}
    diagnostics_total_pair_expansion: dict[str, int] = {}
    if artifact_available and isinstance(call_resolution_diagnostics, dict):
        raw_totals = call_resolution_diagnostics.get("totals")
        if isinstance(raw_totals, dict):
            diagnostics_totals = {
                "observed_syntactic_callsites": int(
                    raw_totals.get("observed_callsites") or 0
                ),
                "filtered_pre_persist": int(
                    raw_totals.get("filtered_before_persist") or 0
                ),
                "persisted_callsites": int(raw_totals.get("persisted_callsites") or 0),
                "persisted_accepted": int(
                    raw_totals.get("finalized_accepted_callsites") or 0
                ),
                "persisted_dropped": int(
                    raw_totals.get("finalized_dropped_callsites") or 0
                ),
            }
            raw_record_drops = raw_totals.get("record_drops")
            if isinstance(raw_record_drops, dict):
                diagnostics_total_record_drops = {
                    str(bucket): int(count or 0)
                    for bucket, count in raw_record_drops.items()
                    if int(count or 0) > 0
                }
            raw_pre_persist_buckets = raw_totals.get("filtered_pre_persist_buckets")
            if isinstance(raw_pre_persist_buckets, dict):
                diagnostics_total_pre_persist_buckets = {
                    str(bucket): int(count or 0)
                    for bucket, count in raw_pre_persist_buckets.items()
                    if int(count or 0) > 0
                }
            raw_pair_expansion = raw_totals.get("persisted_callsite_pair_expansion")
            if isinstance(raw_pair_expansion, dict):
                diagnostics_total_pair_expansion = {
                    str(bucket): int(count or 0)
                    for bucket, count in raw_pair_expansion.items()
                    if int(count or 0) > 0
                }
        raw_by_caller = call_resolution_diagnostics.get("by_caller")
        if isinstance(raw_by_caller, dict):
            for caller_id, raw in raw_by_caller.items():
                if not isinstance(raw, dict):
                    continue
                caller_key = str(caller_id)
                language = caller_language.get(caller_key)
                if not language:
                    continue
                caller_info = caller_metadata.get(caller_key, {})
                scope_key = _scope_bucket(str(caller_info.get("file_path") or ""))
                observed = int(raw.get("observed_callsites") or 0)
                filtered = int(raw.get("filtered_before_persist") or 0)
                persisted = int(raw.get("persisted_callsites") or 0)
                accepted = int(raw.get("finalized_accepted_callsites") or 0)
                dropped = int(raw.get("finalized_dropped_callsites") or 0)
                lang_diag = diagnostics_by_language[language]
                lang_diag["observed_syntactic_callsites"] += observed
                lang_diag["filtered_pre_persist"] += filtered
                lang_diag["persisted_callsites"] += persisted
                lang_diag["persisted_accepted"] += accepted
                lang_diag["persisted_dropped"] += dropped
                scope_diag = diagnostics_by_scope[language][scope_key]
                scope_diag["observed_syntactic_callsites"] = int(
                    scope_diag.get("observed_syntactic_callsites") or 0
                ) + observed
                scope_diag["filtered_pre_persist"] = int(
                    scope_diag.get("filtered_pre_persist") or 0
                ) + filtered
                scope_diag["persisted_callsites"] = int(
                    scope_diag.get("persisted_callsites") or 0
                ) + persisted
                scope_diag["persisted_accepted"] = int(
                    scope_diag.get("persisted_accepted") or 0
                ) + accepted
                scope_diag["persisted_dropped"] = int(
                    scope_diag.get("persisted_dropped") or 0
                ) + dropped
                raw_record_drops = raw.get("record_drops")
                if isinstance(raw_record_drops, dict):
                    scope_record_drops = scope_diag.get("record_drops")
                    if not isinstance(scope_record_drops, dict):
                        scope_record_drops = {}
                        scope_diag["record_drops"] = scope_record_drops
                    language_record_drops = diagnostics_record_drops_by_language[language]
                    for bucket, count in raw_record_drops.items():
                        amount = int(count or 0)
                        if amount <= 0:
                            continue
                        bucket_name = str(bucket)
                        language_record_drops[bucket_name] = (
                            language_record_drops.get(bucket_name, 0) + amount
                        )
                        scope_record_drops[bucket_name] = (
                            int(scope_record_drops.get(bucket_name, 0)) + amount
                        )
                raw_pre_persist_buckets = raw.get("filtered_pre_persist_buckets")
                if isinstance(raw_pre_persist_buckets, dict):
                    scope_pre_persist = scope_diag.get("filtered_pre_persist_buckets")
                    if not isinstance(scope_pre_persist, dict):
                        scope_pre_persist = {}
                        scope_diag["filtered_pre_persist_buckets"] = scope_pre_persist
                    language_pre_persist = diagnostics_pre_persist_buckets_by_language[
                        language
                    ]
                    for bucket, count in raw_pre_persist_buckets.items():
                        amount = int(count or 0)
                        if amount <= 0:
                            continue
                        bucket_name = str(bucket)
                        language_pre_persist[bucket_name] = (
                            language_pre_persist.get(bucket_name, 0) + amount
                        )
                        scope_pre_persist[bucket_name] = (
                            int(scope_pre_persist.get(bucket_name, 0)) + amount
                        )
                raw_pair_expansion = raw.get("persisted_callsite_pair_expansion")
                if isinstance(raw_pair_expansion, dict):
                    scope_pair_expansion = scope_diag.get(
                        "persisted_callsite_pair_expansion"
                    )
                    if not isinstance(scope_pair_expansion, dict):
                        scope_pair_expansion = {}
                        scope_diag["persisted_callsite_pair_expansion"] = (
                            scope_pair_expansion
                        )
                    language_pair_expansion = diagnostics_pair_expansion_by_language[
                        language
                    ]
                    for bucket, count in raw_pair_expansion.items():
                        amount = int(count or 0)
                        if amount <= 0:
                            continue
                        bucket_name = str(bucket)
                        if bucket_name == "max_pairs_for_single_persisted_callsite":
                            language_pair_expansion[bucket_name] = max(
                                int(language_pair_expansion.get(bucket_name, 0)),
                                amount,
                            )
                            scope_pair_expansion[bucket_name] = max(
                                int(scope_pair_expansion.get(bucket_name, 0)),
                                amount,
                            )
                            continue
                        language_pair_expansion[bucket_name] = (
                            int(language_pair_expansion.get(bucket_name, 0)) + amount
                        )
                        scope_pair_expansion[bucket_name] = (
                            int(scope_pair_expansion.get(bucket_name, 0)) + amount
                        )

    rows: list[LanguageMetrics] = []
    structure_scope_counts = {
        "non_tests": {"files": 0, "nodes": 0},
        "tests": {"files": 0, "nodes": 0},
    }
    for items in file_node_distribution_by_language.values():
        for file_path, node_count in items:
            scope_key = _scope_bucket(file_path)
            structure_scope_counts[scope_key]["files"] += 1
            structure_scope_counts[scope_key]["nodes"] += int(node_count)
    for language in sorted(language_metrics.keys()):
        current = language_metrics[language]
        diag_totals = diagnostics_by_language.get(
            language,
            {
                "observed_syntactic_callsites": 0,
                "filtered_pre_persist": 0,
                "persisted_callsites": 0,
                "persisted_accepted": 0,
                "persisted_dropped": 0,
            },
        )
        rows.append(
            LanguageMetrics(
                language=language,
                files=current.files,
                nodes=current.nodes,
                edges=graph_edge_totals.get(language, 0) if artifact_available else None,
                persisted_in_scope_pairs=pair_totals.get(language, 0)
                if artifact_available
                else None,
                finalized_call_edges=call_edge_totals.get(language, 0)
                if artifact_available
                else None,
                observed_syntactic_callsites=diag_totals.get(
                    "observed_syntactic_callsites"
                )
                if artifact_available
                else None,
                filtered_pre_persist=diag_totals.get("filtered_pre_persist")
                if artifact_available
                else None,
                persisted_callsites=diag_totals.get("persisted_callsites")
                if artifact_available
                else None,
                persisted_accepted=diag_totals.get("persisted_accepted")
                if artifact_available
                else None,
                persisted_dropped=diag_totals.get("persisted_dropped")
                if artifact_available
                else None,
                filtered_pre_persist_buckets=diagnostics_pre_persist_buckets_by_language.get(
                    language, {}
                ),
            )
        )

    total_pair_count = (
        sum(item.persisted_in_scope_pairs or 0 for item in rows)
        if artifact_available
        else None
    )
    total_graph_edge_count = (
        sum((item.edges or 0) for item in rows) if artifact_available else None
    )
    total_edge_count = (
        sum(item.finalized_call_edges or 0 for item in rows)
        if artifact_available
        else None
    )

    def _scope_callsites(scope_key: str) -> dict[str, int | None]:
        if not artifact_available:
            return {
                "observed_syntactic_callsites": None,
                "filtered_pre_persist": None,
                "persisted_callsites": None,
                "persisted_accepted": None,
                "persisted_dropped": None,
            }
        return _sum_scope(
            diagnostics_by_scope,
            scope_key=scope_key,
            field_names=(
                "observed_syntactic_callsites",
                "filtered_pre_persist",
                "persisted_callsites",
                "persisted_accepted",
                "persisted_dropped",
            ),
        )

    def _scope_pre_persist(scope_key: str) -> dict[str, int]:
        return _filtered_pre_persist_buckets_payload(
            _sum_scope_nested_buckets(
                diagnostics_by_scope,
                scope_key=scope_key,
                nested_key="filtered_pre_persist_buckets",
            )
            if artifact_available
            else None
        )

    scope_pair_counts = {
        "non_tests": (
            sum(int(scope_counts.get("non_tests", 0)) for scope_counts in pair_scope_totals.values())
            if artifact_available
            else None
        ),
        "tests": (
            sum(int(scope_counts.get("tests", 0)) for scope_counts in pair_scope_totals.values())
            if artifact_available
            else None
        ),
    }
    scope_edge_counts = {
        "non_tests": (
            sum(int(scope_counts.get("non_tests", 0)) for scope_counts in call_edge_scope_totals.values())
            if artifact_available
            else None
        ),
        "tests": (
            sum(int(scope_counts.get("tests", 0)) for scope_counts in call_edge_scope_totals.values())
            if artifact_available
            else None
        ),
    }
    scope_graph_edge_counts = {
        "non_tests": (
            sum(
                int(scope_counts.get("non_tests", 0))
                for scope_counts in graph_edge_scope_totals.values()
            )
            if artifact_available
            else None
        ),
        "tests": (
            sum(
                int(scope_counts.get("tests", 0))
                for scope_counts in graph_edge_scope_totals.values()
            )
            if artifact_available
            else None
        ),
    }

    payload: dict[str, object] = {
        "artifact_db_available": artifact_available,
        "labels": _labels_payload(),
        "timing": {
            "build_total_seconds": build_total_seconds,
            "build_wall_seconds": build_wall_seconds,
            "build_phase_timings": build_phase_timings or {},
        },
        "languages": dict(
            next(iter(item.to_payload().items()))
            for item in rows),
        "totals": {
            "structure": {
                "files": sum(item.files for item in rows),
                "nodes": sum(item.nodes for item in rows),
                "edges": total_graph_edge_count,
            },
            "callsites": {
                "observed_syntactic_callsites": diagnostics_totals.get(
                    "observed_syntactic_callsites"
                )
                if artifact_available
                else None,
                "filtered_pre_persist": diagnostics_totals.get("filtered_pre_persist")
                if artifact_available
                else None,
                "persisted_callsites": diagnostics_totals.get("persisted_callsites")
                if artifact_available
                else None,
                "persisted_accepted": diagnostics_totals.get("persisted_accepted")
                if artifact_available
                else None,
                "persisted_dropped": diagnostics_totals.get("persisted_dropped")
                if artifact_available
                else None,
            },
            "pre_persist_filter": _filtered_pre_persist_buckets_payload(
                diagnostics_total_pre_persist_buckets if artifact_available else None
            ),
            "call_materialization": {
                "callsite_pairs": total_pair_count,
                "finalized_call_edges": total_edge_count,
            },
        },
        "scopes": {
            "non_tests": {
                "structure": {
                    "files": structure_scope_counts["non_tests"]["files"],
                    "nodes": structure_scope_counts["non_tests"]["nodes"],
                    "edges": scope_graph_edge_counts["non_tests"],
                },
                "callsites": _scope_callsites("non_tests"),
                "pre_persist_filter": _scope_pre_persist("non_tests"),
                "call_materialization": {
                    "callsite_pairs": scope_pair_counts["non_tests"],
                    "finalized_call_edges": scope_edge_counts["non_tests"],
                },
            },
            "tests": {
                "structure": {
                    "files": structure_scope_counts["tests"]["files"],
                    "nodes": structure_scope_counts["tests"]["nodes"],
                    "edges": scope_graph_edge_counts["tests"],
                },
                "callsites": _scope_callsites("tests"),
                "pre_persist_filter": _scope_pre_persist("tests"),
                "call_materialization": {
                    "callsite_pairs": scope_pair_counts["tests"],
                    "finalized_call_edges": scope_edge_counts["tests"],
                },
            },
        },
    }
    return payload
def _filtered_pre_persist_buckets_payload(
    buckets: dict[str, int] | None,
) -> dict[str, int]:
    return _filtered_pre_persist_buckets_payload_impl(buckets)


def _scope_bucket(file_path: str) -> str:
    return _scope_bucket_impl(file_path)


def _sum_scope(
    language_scope_totals: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
    field_names: tuple[str, ...],
) -> dict[str, int]:
    result = {field: 0 for field in field_names}
    for scope_counts in language_scope_totals.values():
        scope = scope_counts.get(scope_key, {})
        for field in field_names:
            result[field] += int(scope.get(field, 0))
    return result


def _sum_scope_nested_buckets(
    language_scope_totals: dict[str, dict[str, dict[str, int | dict[str, int]]]],
    *,
    scope_key: str,
    nested_key: str,
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for scope_counts in language_scope_totals.values():
        scope = scope_counts.get(scope_key, {})
        nested = scope.get(nested_key)
        if not isinstance(nested, dict):
            continue
        for bucket, count in nested.items():
            totals[str(bucket)] = totals.get(str(bucket), 0) + int(count)
    return totals


def _sum_record_drop_buckets(
    language_buckets: dict[str, dict[str, int]],
) -> dict[str, int]:
    return _sum_record_drop_buckets_impl(language_buckets)


def _sum_record_drop_buckets_by_scope(
    language_scope_buckets: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
) -> dict[str, int]:
    return _sum_record_drop_buckets_by_scope_impl(
        language_scope_buckets, scope_key=scope_key
    )
