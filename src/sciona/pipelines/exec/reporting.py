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
    call_site_funnel_payload as _call_site_funnel_payload_impl,
    count_payload as _count_payload_impl,
    persisted_callsite_pair_expansion_payload as _persisted_callsite_pair_expansion_payload_impl,
    scope_bucket as _scope_bucket_impl,
    scope_call_site_funnel_payload as _scope_call_site_funnel_payload_impl,
    scope_count_payload as _scope_count_payload_impl,
    scope_persisted_callsite_pair_expansion_payload as _scope_persisted_callsite_pair_expansion_payload_impl,
    sum_record_drop_buckets as _sum_record_drop_buckets_impl,
    sum_record_drop_buckets_by_scope as _sum_record_drop_buckets_by_scope_impl,
    sum_scope as _sum_scope_impl,
)
from .reporting_files import (
    discovered_files_by_language as _discovered_files_by_language_impl,
    structural_density_payload as _structural_density_payload_impl,
)


@dataclass(frozen=True)
class LanguageMetrics:
    language: str
    files: int = 0
    nodes: int = 0
    edges: int = 0
    persisted_in_scope_pairs: int | None = None
    finalized_call_edges: int | None = None
    observed_syntactic_callsites: int | None = None
    filtered_pre_persist: int | None = None
    persisted_callsites: int | None = None
    persisted_accepted: int | None = None
    persisted_dropped: int | None = None
    record_drops: dict[str, int] = field(default_factory=dict)
    filtered_pre_persist_buckets: dict[str, int] = field(default_factory=dict)
    persisted_callsite_pair_expansion: dict[str, int] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "language": self.language,
            "files": self.files,
            "nodes": self.nodes,
            "edges": self.edges,
            "callsite_pairs": _count_payload(self.persisted_in_scope_pairs),
            "finalized_call_edges": _count_payload(self.finalized_call_edges),
            "call_site_funnel": _call_site_funnel_payload(
                observed_syntactic_callsites=self.observed_syntactic_callsites,
                filtered_pre_persist=self.filtered_pre_persist,
                persisted_callsites=self.persisted_callsites,
                persisted_accepted=self.persisted_accepted,
                persisted_dropped=self.persisted_dropped,
                record_drops=self.record_drops,
            ),
            "persisted_callsite_pair_expansion": _persisted_callsite_pair_expansion_payload(
                persisted_callsites=self.persisted_callsites,
                persisted_callsites_with_zero_pairs=self.persisted_callsite_pair_expansion.get(
                    "persisted_callsites_with_zero_pairs",
                    0,
                ),
                persisted_callsites_with_one_pair=self.persisted_callsite_pair_expansion.get(
                    "persisted_callsites_with_one_pair",
                    0,
                ),
                persisted_callsites_with_multiple_pairs=self.persisted_callsite_pair_expansion.get(
                    "persisted_callsites_with_multiple_pairs",
                    0,
                ),
                pair_count=self.persisted_in_scope_pairs,
                max_pairs_for_single_persisted_callsite=self.persisted_callsite_pair_expansion.get(
                    "max_pairs_for_single_persisted_callsite",
                    0,
                ),
            ),
        }
        if self.filtered_pre_persist_buckets:
            payload["filtered_pre_persist_buckets"] = dict(
                sorted(self.filtered_pre_persist_buckets.items())
            )
        return payload


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
    discovered_files_by_language = _discovered_files_by_language(repo_state.repo_root)
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
        edge_counts = core_read.language_edge_counts(conn, snapshot_id)
        for item in edge_counts:
            language = str(item["language"])
            current = language_metrics.get(language, LanguageMetrics(language=language))
            language_metrics[language] = LanguageMetrics(
                language=language,
                files=current.files,
                nodes=current.nodes,
                edges=int(item["edge_count"] or 0),
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
                edges=current.edges,
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
                record_drops=diagnostics_record_drops_by_language.get(language, {}),
                filtered_pre_persist_buckets=diagnostics_pre_persist_buckets_by_language.get(
                    language, {}
                ),
                persisted_callsite_pair_expansion=diagnostics_pair_expansion_by_language.get(
                    language, {}
                ),
            )
        )

    payload: dict[str, object] = {
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "build_total_seconds": build_total_seconds,
        "build_wall_seconds": build_wall_seconds,
        "build_phase_timings": build_phase_timings or {},
        "artifact_db_available": artifact_available,
        "callsite_pairs_semantics": "deduplicated_persisted_in_scope_candidate_pairs",
        "finalized_call_edges_semantics": "deduplicated_graph_edges_derived_from_callsite_pairs",
        "languages": [item.to_payload() for item in rows],
        "totals": {
            "files": sum(item.files for item in rows),
            "nodes": sum(item.nodes for item in rows),
            "edges": sum(item.edges for item in rows),
            "callsite_pairs": _count_payload(
                sum(item.persisted_in_scope_pairs or 0 for item in rows)
                if artifact_available
                else None
            ),
            "finalized_call_edges": _count_payload(
                sum(item.finalized_call_edges or 0 for item in rows)
                if artifact_available
                else None
            ),
            "call_site_funnel": _call_site_funnel_payload(
                observed_syntactic_callsites=diagnostics_totals.get(
                    "observed_syntactic_callsites"
                )
                if artifact_available
                else None,
                filtered_pre_persist=diagnostics_totals.get("filtered_pre_persist")
                if artifact_available
                else None,
                persisted_callsites=diagnostics_totals.get("persisted_callsites")
                if artifact_available
                else None,
                persisted_accepted=diagnostics_totals.get("persisted_accepted")
                if artifact_available
                else None,
                persisted_dropped=diagnostics_totals.get("persisted_dropped")
                if artifact_available
                else None,
                record_drops=diagnostics_total_record_drops if artifact_available else None,
            ),
            "persisted_callsite_pair_expansion": _persisted_callsite_pair_expansion_payload(
                persisted_callsites=diagnostics_totals.get("persisted_callsites")
                if artifact_available
                else None,
                persisted_callsites_with_zero_pairs=diagnostics_total_pair_expansion.get(
                    "persisted_callsites_with_zero_pairs",
                    0,
                )
                if artifact_available
                else None,
                persisted_callsites_with_one_pair=diagnostics_total_pair_expansion.get(
                    "persisted_callsites_with_one_pair",
                    0,
                )
                if artifact_available
                else None,
                persisted_callsites_with_multiple_pairs=diagnostics_total_pair_expansion.get(
                    "persisted_callsites_with_multiple_pairs",
                    0,
                )
                if artifact_available
                else None,
                pair_count=(
                    sum(item.persisted_in_scope_pairs or 0 for item in rows)
                    if artifact_available
                    else None
                ),
                max_pairs_for_single_persisted_callsite=diagnostics_total_pair_expansion.get(
                    "max_pairs_for_single_persisted_callsite",
                    0,
                )
                if artifact_available
                else None,
            ),
            "callsite_pairs_by_scope": _scope_count_payload(
                {
                    "non_tests": sum(
                        int(scope_counts.get("non_tests", 0))
                        for scope_counts in pair_scope_totals.values()
                    ),
                    "tests": sum(
                        int(scope_counts.get("tests", 0))
                        for scope_counts in pair_scope_totals.values()
                    ),
                }
                if artifact_available
                else None
            ),
            "finalized_call_edges_by_scope": _scope_count_payload(
                {
                    "non_tests": sum(
                        int(scope_counts.get("non_tests", 0))
                        for scope_counts in call_edge_scope_totals.values()
                    ),
                    "tests": sum(
                        int(scope_counts.get("tests", 0))
                        for scope_counts in call_edge_scope_totals.values()
                    ),
                }
                if artifact_available
                else None
            ),
            "call_site_funnel_by_scope": _scope_call_site_funnel_payload(
                {
                    "non_tests": {
                        **_sum_scope(
                            diagnostics_by_scope,
                            scope_key="non_tests",
                            field_names=(
                                "observed_syntactic_callsites",
                                "filtered_pre_persist",
                                "persisted_callsites",
                                "persisted_accepted",
                                "persisted_dropped",
                            ),
                        ),
                        "record_drops": _sum_record_drop_buckets_by_scope(
                            diagnostics_by_scope, scope_key="non_tests"
                        ),
                    },
                    "tests": {
                        **_sum_scope(
                            diagnostics_by_scope,
                            scope_key="tests",
                            field_names=(
                                "observed_syntactic_callsites",
                                "filtered_pre_persist",
                                "persisted_callsites",
                                "persisted_accepted",
                                "persisted_dropped",
                            ),
                        ),
                        "record_drops": _sum_record_drop_buckets_by_scope(
                            diagnostics_by_scope, scope_key="tests"
                        ),
                    },
                }
                if artifact_available
                else None
            ),
            "persisted_callsite_pair_expansion_by_scope": _scope_persisted_callsite_pair_expansion_payload(
                {
                    "non_tests": {
                        **_sum_scope(
                            diagnostics_by_scope,
                            scope_key="non_tests",
                            field_names=(
                                "persisted_callsites",
                            ),
                        ),
                        **_sum_scope_nested_max(
                            diagnostics_by_scope,
                            scope_key="non_tests",
                            nested_key="persisted_callsite_pair_expansion",
                            field_names=(
                                "persisted_callsites_with_zero_pairs",
                                "persisted_callsites_with_one_pair",
                                "persisted_callsites_with_multiple_pairs",
                            ),
                            max_field="max_pairs_for_single_persisted_callsite",
                        ),
                    },
                    "tests": {
                        **_sum_scope(
                            diagnostics_by_scope,
                            scope_key="tests",
                            field_names=(
                                "persisted_callsites",
                            ),
                        ),
                        **_sum_scope_nested_max(
                            diagnostics_by_scope,
                            scope_key="tests",
                            nested_key="persisted_callsite_pair_expansion",
                            field_names=(
                                "persisted_callsites_with_zero_pairs",
                                "persisted_callsites_with_one_pair",
                                "persisted_callsites_with_multiple_pairs",
                            ),
                            max_field="max_pairs_for_single_persisted_callsite",
                        ),
                    },
                }
                if artifact_available
                else None,
                pair_scope_counts=(
                    {
                        "non_tests": sum(
                            int(scope_counts.get("non_tests", 0))
                            for scope_counts in pair_scope_totals.values()
                        ),
                        "tests": sum(
                            int(scope_counts.get("tests", 0))
                            for scope_counts in pair_scope_totals.values()
                        ),
                    }
                    if artifact_available
                    else None
                ),
            ),
        },
    }
    if diagnostics_total_pre_persist_buckets:
        payload["totals"]["filtered_pre_persist_buckets"] = dict(
            sorted(diagnostics_total_pre_persist_buckets.items())
        )

    for item in payload["languages"]:
        language = str(item.get("language") or "")
        if not language:
            continue
        item["callsite_pairs_by_scope"] = _scope_count_payload(
            pair_scope_totals.get(language, {"non_tests": 0, "tests": 0})
            if artifact_available
            else None
        )
        item["finalized_call_edges_by_scope"] = _scope_count_payload(
            call_edge_scope_totals.get(language, {"non_tests": 0, "tests": 0})
            if artifact_available
            else None
        )
        item["call_site_funnel_by_scope"] = _scope_call_site_funnel_payload(
            diagnostics_by_scope.get(language) if artifact_available else None
        )
        item["persisted_callsite_pair_expansion_by_scope"] = (
            _scope_persisted_callsite_pair_expansion_payload(
                diagnostics_by_scope.get(language) if artifact_available else None,
                pair_scope_counts=(
                    pair_scope_totals.get(language, {"non_tests": 0, "tests": 0})
                    if artifact_available
                    else None
                ),
            )
        )
        item["structural_density"] = _structural_density_payload(
            files=int(item.get("files") or 0),
            nodes=int(item.get("nodes") or 0),
            eligible_callsites=int((item.get("callsite_pairs") or {}).get("count") or 0),
            file_node_distribution=file_node_distribution_by_language.get(language, []),
            discovered_files=discovered_files_by_language.get(language),
        )

    all_distribution: list[tuple[str, int]] = []
    for items in file_node_distribution_by_language.values():
        all_distribution.extend(items)
    payload["totals"]["structural_density"] = _structural_density_payload(
        files=int(payload["totals"].get("files") or 0),
        nodes=int(payload["totals"].get("nodes") or 0),
        eligible_callsites=int(
            (payload["totals"].get("callsite_pairs") or {}).get("count") or 0
        ),
        file_node_distribution=all_distribution,
        discovered_files=(
            sum(int(v) for v in discovered_files_by_language.values())
            if discovered_files_by_language
            else None
        ),
    )
    return payload


def _count_payload(count: int | None) -> dict[str, object]:
    return _count_payload_impl(count)


def _call_site_funnel_payload(
    *,
    observed_syntactic_callsites: int | None,
    filtered_pre_persist: int | None,
    persisted_callsites: int | None,
    persisted_accepted: int | None,
    persisted_dropped: int | None,
    record_drops: dict[str, int] | None = None,
) -> dict[str, object]:
    return _call_site_funnel_payload_impl(
        observed_syntactic_callsites=observed_syntactic_callsites,
        filtered_pre_persist=filtered_pre_persist,
        persisted_callsites=persisted_callsites,
        persisted_accepted=persisted_accepted,
        persisted_dropped=persisted_dropped,
        record_drops=record_drops,
    )


def _persisted_callsite_pair_expansion_payload(
    *,
    persisted_callsites: int | None,
    persisted_callsites_with_zero_pairs: int | None,
    persisted_callsites_with_one_pair: int | None,
    persisted_callsites_with_multiple_pairs: int | None,
    pair_count: int | None,
    max_pairs_for_single_persisted_callsite: int | None,
) -> dict[str, object]:
    return _persisted_callsite_pair_expansion_payload_impl(
        persisted_callsites=persisted_callsites,
        persisted_callsites_with_zero_pairs=persisted_callsites_with_zero_pairs,
        persisted_callsites_with_one_pair=persisted_callsites_with_one_pair,
        persisted_callsites_with_multiple_pairs=persisted_callsites_with_multiple_pairs,
        pair_count=pair_count,
        max_pairs_for_single_persisted_callsite=max_pairs_for_single_persisted_callsite,
    )


def _scope_bucket(file_path: str) -> str:
    return _scope_bucket_impl(file_path)


def _scope_count_payload(
    scope_counts: dict[str, int] | None,
) -> dict[str, dict[str, object]] | None:
    return _scope_count_payload_impl(scope_counts)


def _scope_persisted_callsite_pair_expansion_payload(
    scope_counts: dict[str, dict[str, object]] | None,
    *,
    pair_scope_counts: dict[str, int] | None,
) -> dict[str, dict[str, object]] | None:
    return _scope_persisted_callsite_pair_expansion_payload_impl(
        scope_counts,
        pair_scope_counts=pair_scope_counts,
    )


def _scope_call_site_funnel_payload(
    scope_counts: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, object]] | None:
    return _scope_call_site_funnel_payload_impl(scope_counts)


def _structural_density_payload(
    *,
    files: int,
    nodes: int,
    eligible_callsites: int,
    file_node_distribution: list[tuple[str, int]],
    discovered_files: int | None,
) -> dict[str, object]:
    return _structural_density_payload_impl(
        files=files,
        nodes=nodes,
        eligible_callsites=eligible_callsites,
        file_node_distribution=file_node_distribution,
        discovered_files=discovered_files,
    )


def _discovered_files_by_language(repo_root) -> dict[str, int]:
    return _discovered_files_by_language_impl(repo_root)


def _sum_scope(
    language_scope_totals: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
    field_names: tuple[str, ...],
) -> dict[str, int]:
    return _sum_scope_impl(
        language_scope_totals, scope_key=scope_key, field_names=field_names
    )


def _sum_scope_nested_max(
    language_scope_totals: dict[str, dict[str, dict[str, int | dict[str, int]]]],
    *,
    scope_key: str,
    nested_key: str,
    field_names: tuple[str, ...],
    max_field: str,
) -> dict[str, int]:
    result = {field: 0 for field in field_names}
    result[max_field] = 0
    for scope_counts in language_scope_totals.values():
        scope = scope_counts.get(scope_key, {})
        nested = scope.get(nested_key)
        if not isinstance(nested, dict):
            continue
        for field in field_names:
            result[field] += int(nested.get(field, 0))
        result[max_field] = max(result[max_field], int(nested.get(max_field, 0)))
    return result


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
