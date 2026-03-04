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
        return payload


def snapshot_report(
    repo_state: RepoState,
    *,
    snapshot_id: str,
    include_failure_reasons: bool = False,
) -> dict[str, object] | None:
    language_metrics: dict[str, LanguageMetrics] = {}
    caller_language: dict[str, str] = {}
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
        caller_language = core_read.caller_language_map(conn, snapshot_id)

    artifact_available = False
    call_site_reasons: dict[str, dict[str, int]] = defaultdict(dict)
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
    except sqlite3.Error:
        artifact_available = False

    languages = sorted(language_metrics.keys())
    rows: list[LanguageMetrics] = []
    for language in languages:
        current = language_metrics[language]
        rows.append(
            LanguageMetrics(
                language=language,
                files=current.files,
                nodes=current.nodes,
                edges=current.edges,
                call_sites_eligible=call_site_totals.get(language, {}).get("eligible")
                if artifact_available
                else None,
                call_sites_accepted=call_site_totals.get(language, {}).get("accepted")
                if artifact_available
                else None,
                call_sites_dropped=call_site_totals.get(language, {}).get("dropped")
                if artifact_available
                else None,
                drop_reasons=call_site_reasons.get(language, {}),
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

    return {
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


__all__ = ["snapshot_report"]
