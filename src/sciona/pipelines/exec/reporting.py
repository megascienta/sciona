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
    drop_reason_examples: dict[str, list[dict[str, object]]] = field(default_factory=dict)

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
        if include_failure_reasons and self.drop_reason_examples:
            payload["drop_reason_examples"] = {
                reason: examples
                for reason, examples in sorted(self.drop_reason_examples.items())
            }
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
            )
        caller_metadata = core_read.caller_node_metadata_map(conn, snapshot_id)
        caller_language = {
            structural_id: str(meta["language"])
            for structural_id, meta in caller_metadata.items()
        }

    artifact_available = False
    call_site_reasons: dict[str, dict[str, int]] = defaultdict(dict)
    call_site_reason_examples: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(dict)
    failure_hotspots_callers: dict[str, dict[str, int]] = defaultdict(dict)
    failure_hotspots_files: dict[str, dict[str, int]] = defaultdict(dict)
    call_site_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"eligible": 0, "accepted": 0, "dropped": 0}
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
                call_site_totals[language]["eligible"] += count
                status = str(item["resolution_status"])
                if status == "accepted":
                    call_site_totals[language]["accepted"] += count
                else:
                    call_site_totals[language]["dropped"] += count
                    if include_failure_reasons:
                        reason = str(item["drop_reason"] or "unknown")
                        call_site_reasons[language][reason] = (
                            call_site_reasons[language].get(reason, 0) + count
                        )
            if include_failure_reasons:
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
                drop_reason_examples=call_site_reason_examples.get(language, {}),
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
        },
    }
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


__all__ = ["snapshot_report"]
