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
from ...data_storage.artifact_db import read_reporting as artifact_reporting


@dataclass(frozen=True)
class LanguageMetrics:
    language: str
    files: int = 0
    nodes: int = 0
    edges: int = 0
    call_sites_eligible: int | None = None
    call_sites_accepted: int | None = None
    call_sites_dropped: int | None = None
    drop_reasons: dict[str, int] = field(default_factory=dict)
    drop_classification: dict[str, int] = field(default_factory=dict)
    drop_classification_by_scope: dict[str, dict[str, int]] = field(default_factory=dict)
    drop_reason_examples: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    accepted_examples: list[dict[str, object]] = field(default_factory=list)

    def to_payload(self, *, include_failure_reasons: bool) -> dict[str, object]:
        payload: dict[str, object] = {
            "language": self.language,
            "files": self.files,
            "nodes": self.nodes,
            "edges": self.edges,
        }
        payload["call_sites"] = _call_sites_payload(
            self.call_sites_eligible,
            self.call_sites_accepted,
            self.call_sites_dropped,
        )
        if include_failure_reasons and self.drop_reasons:
            payload["drop_reasons"] = dict(sorted(self.drop_reasons.items()))
        if include_failure_reasons and self.drop_classification:
            payload["drop_classification"] = dict(sorted(self.drop_classification.items()))
        if include_failure_reasons and self.drop_classification_by_scope:
            payload["drop_classification_by_scope"] = {
                scope: dict(sorted(counts.items()))
                for scope, counts in sorted(self.drop_classification_by_scope.items())
            }
        if include_failure_reasons and self.drop_reason_examples:
            payload["drop_reason_examples"] = {
                reason: examples
                for reason, examples in sorted(self.drop_reason_examples.items())
            }
        if include_failure_reasons and self.accepted_examples:
            payload["accepted_examples"] = list(self.accepted_examples)
        return payload


def snapshot_report(
    repo_state: RepoState,
    *,
    snapshot_id: str,
    include_failure_reasons: bool = False,
) -> dict[str, object] | None:
    language_metrics: dict[str, LanguageMetrics] = {}
    caller_language: dict[str, str] = {}
    caller_metadata: dict[str, dict[str, object]] = {}
    created_at: str | None = None

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
                call_sites_eligible=current.call_sites_eligible,
                call_sites_accepted=current.call_sites_accepted,
                call_sites_dropped=current.call_sites_dropped,
                drop_reasons=current.drop_reasons,
                drop_classification=current.drop_classification,
                drop_classification_by_scope=current.drop_classification_by_scope,
            )
        caller_metadata = core_read.caller_node_metadata_map(conn, snapshot_id)
        caller_language = {
            structural_id: str(meta["language"])
            for structural_id, meta in caller_metadata.items()
        }

    artifact_available = False
    call_site_reasons: dict[str, dict[str, int]] = defaultdict(dict)
    drop_classification: dict[str, dict[str, int]] = defaultdict(dict)
    drop_classification_by_scope: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: {"non_tests": {}, "tests": {}}
    )
    call_site_reason_examples: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(dict)
    call_site_accept_examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    failure_hotspots_callers: dict[str, dict[str, int]] = defaultdict(dict)
    failure_hotspots_files: dict[str, dict[str, int]] = defaultdict(dict)
    call_site_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"eligible": 0, "accepted": 0, "dropped": 0}
    )
    call_site_scope_totals: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: {
            "non_tests": {"eligible": 0, "accepted": 0, "dropped": 0},
            "tests": {"eligible": 0, "accepted": 0, "dropped": 0},
        }
    )
    try:
        with artifact_readonly(
            repo_state.artifact_db_path, repo_root=repo_state.repo_root
        ) as conn:
            artifact_available = True
            call_sites = artifact_reporting.call_site_caller_status_counts(
                conn,
                snapshot_id=snapshot_id,
            )
            for item in call_sites:
                language = caller_language.get(str(item["caller_id"]))
                if not language:
                    continue
                count = int(item["site_count"] or 0)
                caller_info = caller_metadata.get(str(item["caller_id"])) or {}
                caller_file_path = str(caller_info.get("file_path") or "")
                scope_key = _scope_bucket(caller_file_path)
                call_site_totals[language]["eligible"] += count
                call_site_scope_totals[language][scope_key]["eligible"] += count
                status = str(item["resolution_status"])
                if status == "accepted":
                    call_site_totals[language]["accepted"] += count
                    call_site_scope_totals[language][scope_key]["accepted"] += count
                else:
                    call_site_totals[language]["dropped"] += count
                    call_site_scope_totals[language][scope_key]["dropped"] += count
                    if include_failure_reasons:
                        reason = str(item["drop_reason"] or "unknown")
                        call_site_reasons[language][reason] = (
                            call_site_reasons[language].get(reason, 0) + count
                        )
            if include_failure_reasons:
                dropped_identifiers = artifact_reporting.call_site_drop_identifier_counts(
                    conn,
                    snapshot_id=snapshot_id,
                )
                for item in dropped_identifiers:
                    caller_id = str(item["caller_id"])
                    language = caller_language.get(caller_id)
                    if not language:
                        continue
                    caller_info = caller_metadata.get(caller_id, {})
                    scope_key = _scope_bucket(str(caller_info.get("file_path") or ""))
                    bucket = _drop_classification_bucket(
                        identifier=str(item.get("identifier") or ""),
                        drop_reason=str(item.get("drop_reason") or ""),
                        candidate_count=int(item.get("candidate_count") or 0),
                        callee_kind=str(item.get("callee_kind") or ""),
                    )
                    if not bucket:
                        continue
                    count = int(item.get("site_count") or 0)
                    drop_classification[language][bucket] = (
                        drop_classification[language].get(bucket, 0) + count
                    )
                    scoped = drop_classification_by_scope[language][scope_key]
                    scoped[bucket] = scoped.get(bucket, 0) + count
                dropped_sites = artifact_reporting.call_site_drop_debug_counts(
                    conn,
                    snapshot_id=snapshot_id,
                )
                for item in dropped_sites:
                    caller_id = str(item["caller_id"])
                    language = caller_language.get(caller_id)
                    if not language:
                        continue
                    caller_info = caller_metadata.get(caller_id, {})
                    caller_qname = str(
                        caller_info.get("qualified_name") or item.get("caller_qname") or ""
                    )
                    caller_file_path = str(caller_info.get("file_path") or "")
                    count = int(item.get("site_count") or 0)
                    if caller_qname:
                        failure_hotspots_callers[language][caller_qname] = (
                            failure_hotspots_callers[language].get(caller_qname, 0) + count
                        )
                    if caller_file_path:
                        failure_hotspots_files[language][caller_file_path] = (
                            failure_hotspots_files[language].get(caller_file_path, 0) + count
                        )
                    reason = str(item["drop_reason"] or "unknown")
                    by_reason = call_site_reason_examples[language].setdefault(reason, [])
                    if len(by_reason) >= 8:
                        continue
                    by_reason.append(
                        {
                            "caller_id": caller_id,
                            "caller_qname": caller_qname,
                            "caller_file_path": caller_file_path or None,
                            "caller_node_type": caller_info.get("node_type"),
                            "caller_span": [
                                caller_info.get("start_line"),
                                caller_info.get("end_line"),
                            ],
                            "identifier": str(item.get("identifier") or ""),
                            "candidate_count": int(item.get("candidate_count") or 0),
                            "callee_kind": str(item.get("callee_kind") or ""),
                            "count": count,
                        }
                    )
                accepted_sites = artifact_reporting.call_site_accept_debug_counts(
                    conn,
                    snapshot_id=snapshot_id,
                )
                for item in accepted_sites:
                    caller_id = str(item["caller_id"])
                    language = caller_language.get(caller_id)
                    if not language:
                        continue
                    examples = call_site_accept_examples[language]
                    if len(examples) >= 8:
                        continue
                    caller_info = caller_metadata.get(caller_id, {})
                    examples.append(
                        {
                            "caller_id": caller_id,
                            "caller_qname": str(
                                caller_info.get("qualified_name")
                                or item.get("caller_qname")
                                or ""
                            ),
                            "caller_file_path": str(caller_info.get("file_path") or "") or None,
                            "caller_node_type": caller_info.get("node_type"),
                            "caller_span": [
                                caller_info.get("start_line"),
                                caller_info.get("end_line"),
                            ],
                            "identifier": str(item.get("identifier") or ""),
                            "accepted_callee_id": str(item.get("accepted_callee_id") or ""),
                            "provenance": str(item.get("provenance") or ""),
                            "candidate_count": int(item.get("candidate_count") or 0),
                            "callee_kind": str(item.get("callee_kind") or ""),
                            "count": int(item.get("site_count") or 0),
                        }
                    )
    except sqlite3.Error:
        artifact_available = False

    languages = sorted(language_metrics.keys())
    rows: list[LanguageMetrics] = []
    for language in languages:
        current = language_metrics[language]
        call_totals = call_site_totals.get(
            language,
            {"eligible": 0, "accepted": 0, "dropped": 0},
        )
        rows.append(
            LanguageMetrics(
                language=language,
                files=current.files,
                nodes=current.nodes,
                edges=current.edges,
                call_sites_eligible=call_totals.get("eligible")
                if artifact_available
                else None,
                call_sites_accepted=call_totals.get("accepted")
                if artifact_available
                else None,
                call_sites_dropped=call_totals.get("dropped")
                if artifact_available
                else None,
                drop_reasons=call_site_reasons.get(language, {}),
                drop_classification=drop_classification.get(language, {}),
                drop_classification_by_scope=drop_classification_by_scope.get(
                    language, {}
                ),
                drop_reason_examples=call_site_reason_examples.get(language, {}),
                accepted_examples=call_site_accept_examples.get(language, []),
            )
        )

    total_files = sum(item.files for item in rows)
    total_nodes = sum(item.nodes for item in rows)
    total_edges = sum(item.edges for item in rows)
    total_eligible = (
        sum(item.call_sites_eligible or 0 for item in rows) if artifact_available else None
    )
    total_accepted = (
        sum(item.call_sites_accepted or 0 for item in rows) if artifact_available else None
    )
    total_dropped = (
        sum(item.call_sites_dropped or 0 for item in rows) if artifact_available else None
    )

    payload: dict[str, object] = {
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "artifact_db_available": artifact_available,
        "languages": [
            item.to_payload(include_failure_reasons=include_failure_reasons)
            for item in rows
        ],
        "totals": {
            "files": total_files,
            "nodes": total_nodes,
            "edges": total_edges,
            "call_sites": _call_sites_payload(total_eligible, total_accepted, total_dropped),
            "call_sites_by_scope": _scope_call_sites_payload(
                {
                    "non_tests": _sum_scope(
                        call_site_scope_totals, scope_key="non_tests", field_names=("eligible", "accepted", "dropped")
                    ),
                    "tests": _sum_scope(
                        call_site_scope_totals, scope_key="tests", field_names=("eligible", "accepted", "dropped")
                    ),
                }
                if artifact_available
                else None
            ),
        },
    }
    if include_failure_reasons and artifact_available:
        payload["totals"]["drop_classification"] = _sum_bucket_counts(drop_classification)
        payload["totals"]["drop_classification_by_scope"] = {
            "non_tests": _sum_bucket_counts_by_scope(
                drop_classification_by_scope, scope_key="non_tests"
            ),
            "tests": _sum_bucket_counts_by_scope(
                drop_classification_by_scope, scope_key="tests"
            ),
        }
    for item in payload["languages"]:
        language = str(item.get("language") or "")
        if not language:
            continue
        scope_counts = (
            call_site_scope_totals.get(
                language,
                {
                    "non_tests": {"eligible": 0, "accepted": 0, "dropped": 0},
                    "tests": {"eligible": 0, "accepted": 0, "dropped": 0},
                },
            )
            if artifact_available
            else None
        )
        item["call_sites_by_scope"] = _scope_call_sites_payload(scope_counts)
    if include_failure_reasons:
        payload["failure_hotspots"] = {
            "top_failed_callers": {
                language: _top_items(counts, limit=10)
                for language, counts in sorted(failure_hotspots_callers.items())
            },
            "top_failed_files": {
                language: _top_items(counts, limit=10)
                for language, counts in sorted(failure_hotspots_files.items())
            },
        }
    return payload


def _call_sites_payload(
    eligible: int | None,
    accepted: int | None,
    dropped: int | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "eligible": eligible,
        "accepted": accepted,
        "dropped": dropped,
        "success_rate": None,
    }
    if eligible is None or accepted is None:
        return payload
    if eligible > 0:
        payload["success_rate"] = accepted / eligible
    return payload


def _top_items(items: dict[str, int], *, limit: int) -> list[dict[str, object]]:
    ordered = sorted(items.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"name": name, "count": int(count)} for name, count in ordered]


def _scope_bucket(file_path: str) -> str:
    if not file_path:
        return "non_tests"
    parts = [segment for segment in file_path.replace("\\", "/").split("/") if segment]
    return "tests" if any(part in {"test", "tests"} for part in parts) else "non_tests"


def _scope_call_sites_payload(
    scope_counts: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, object]] | None:
    if scope_counts is None:
        return None
    payload: dict[str, dict[str, object]] = {}
    for scope_key in ("non_tests", "tests"):
        counts = scope_counts.get(scope_key, {"eligible": 0, "accepted": 0, "dropped": 0})
        payload[scope_key] = _call_sites_payload(
            int(counts.get("eligible", 0)),
            int(counts.get("accepted", 0)),
            int(counts.get("dropped", 0)),
        )
    return payload


def _drop_classification_bucket(
    *,
    identifier: str,
    drop_reason: str,
    candidate_count: int,
    callee_kind: str,
) -> str | None:
    if (
        drop_reason == "ambiguous_no_in_scope_candidate"
        and callee_kind == "qualified"
        and candidate_count >= 3
        and "." in identifier
    ):
        return "external_likely"
    return None


def _sum_bucket_counts(
    language_buckets: dict[str, dict[str, int]],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for buckets in language_buckets.values():
        for bucket, count in buckets.items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


def _sum_bucket_counts_by_scope(
    language_scope_buckets: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for scope_map in language_scope_buckets.values():
        for bucket, count in (scope_map.get(scope_key) or {}).items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


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


__all__ = ["snapshot_report"]
