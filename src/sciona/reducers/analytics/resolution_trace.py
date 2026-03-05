# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Call-resolution trace reducer."""

from __future__ import annotations

from typing import Any

from ...code_analysis.core.extract.languages.call_resolution_kernel import (
    REQUIRED_RESOLUTION_STAGES,
)
from ..helpers import queries
from ..helpers.artifact_graph_edges import load_call_resolution_diagnostics
from ..helpers.context import current_artifact_connection, fallback_artifact_connection
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="resolution_trace",
    category="analytics",
    scope="callable",
    placeholders=("RESOLUTION_TRACE",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Call-resolution diagnostics and sampled traces for one callable. "
    "Use to understand why callsites were accepted or dropped without changing CALLS truth. "
    "Scope: callable-level telemetry. Payload kind: summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    function_id: str | None = None,
    method_id: str | None = None,
    identifier: str | None = None,
    limit: int = 25,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="resolution_trace reducer"
    )
    resolved_callable_id = _resolve_callable_id(
        conn,
        snapshot_id,
        callable_id=callable_id,
        function_id=function_id,
        method_id=method_id,
    )
    limit_value = _normalize_limit(limit)
    caller_meta = _caller_metadata(conn, snapshot_id, resolved_callable_id)
    diagnostics = load_call_resolution_diagnostics(
        repo_root,
        snapshot_id=snapshot_id,
        caller_id=resolved_callable_id,
    )
    artifact_conn = current_artifact_connection()
    owns_connection = False
    if artifact_conn is None:
        artifact_conn = fallback_artifact_connection(repo_root)
        owns_connection = artifact_conn is not None
    call_sites: list[dict[str, Any]] = []
    if artifact_conn is not None:
        call_sites = _load_caller_call_sites(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id=resolved_callable_id,
            identifier=identifier,
        )
    accepted, dropped = _split_call_sites(call_sites, limit=limit_value)
    totals = _totals(call_sites)
    body = {
        "payload_kind": "summary",
        "callable_id": resolved_callable_id,
        "callable_qualified_name": caller_meta.get("qualified_name"),
        "callable_file_path": caller_meta.get("file_path"),
        "callable_language": caller_meta.get("language"),
        "artifact_available": artifact_conn is not None,
        "resolution_pipeline_stages": [
            *REQUIRED_RESOLUTION_STAGES,
            "strict_candidate_gate",
        ],
        "identifier_filter": identifier or None,
        "totals": totals,
        "accepted_by_provenance": _sorted_bucket_items(
            diagnostics.get("accepted_by_provenance")
        ),
        "dropped_by_reason": _sorted_bucket_items(diagnostics.get("dropped_by_reason")),
        "candidate_count_histogram": _sorted_histogram_items(
            diagnostics.get("candidate_count_histogram")
        ),
        "diagnostics": {
            "identifiers_total": int(diagnostics.get("identifiers_total") or 0),
            "accepted_identifiers": int(diagnostics.get("accepted_identifiers") or 0),
            "dropped_identifiers": int(diagnostics.get("dropped_identifiers") or 0),
            "assembler_accepted_artifact_dropped": int(
                diagnostics.get("assembler_accepted_artifact_dropped") or 0
            ),
            "record_drops": _sorted_bucket_items(diagnostics.get("record_drops")),
        },
        "accepted_samples": accepted,
        "dropped_samples": dropped,
        "sample_limit": limit_value,
    }
    if owns_connection and artifact_conn is not None:
        artifact_conn.close()
    return render_json_payload(body)


def _resolve_callable_id(
    conn,
    snapshot_id: str,
    *,
    callable_id: str | None,
    function_id: str | None,
    method_id: str | None,
) -> str:
    resolved_function_id = function_id
    if callable_id and not (function_id or method_id):
        resolved_function_id = callable_id
    if method_id:
        return queries.resolve_method_id(conn, snapshot_id, method_id)
    return queries.resolve_function_id(conn, snapshot_id, resolved_function_id)


def _normalize_limit(limit: int) -> int:
    value = int(limit)
    if value <= 0:
        raise ValueError("resolution_trace limit must be a positive integer.")
    return value


def _caller_metadata(conn, snapshot_id: str, caller_id: str) -> dict[str, object]:
    row = conn.execute(
        """
        SELECT sn.language, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
          ON ni.structural_id = sn.structural_id
         AND ni.snapshot_id = ?
        WHERE sn.structural_id = ?
        LIMIT 1
        """,
        (snapshot_id, caller_id),
    ).fetchone()
    if row is None:
        return {}
    return {
        "language": row["language"],
        "qualified_name": row["qualified_name"],
        "file_path": row["file_path"],
    }


def _load_caller_call_sites(
    artifact_conn,
    *,
    snapshot_id: str,
    caller_id: str,
    identifier: str | None,
) -> list[dict[str, Any]]:
    clauses = ["snapshot_id = ?", "caller_id = ?"]
    params: list[object] = [snapshot_id, caller_id]
    if identifier:
        clauses.append("identifier = ?")
        params.append(identifier)
    where = " AND ".join(clauses)
    rows = artifact_conn.execute(
        f"""
        SELECT
            identifier,
            resolution_status,
            accepted_callee_id,
            provenance,
            drop_reason,
            candidate_count,
            callee_kind,
            call_start_byte,
            call_end_byte,
            call_ordinal,
            site_hash
        FROM call_sites
        WHERE {where}
        ORDER BY identifier, call_ordinal, site_hash
        """,
        tuple(params),
    ).fetchall()
    return [dict(row) for row in rows]


def _split_call_sites(
    rows: list[dict[str, Any]],
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for row in rows:
        normalized = _normalize_sample(row)
        if row.get("resolution_status") == "accepted":
            if len(accepted) < limit:
                accepted.append(normalized)
            continue
        if len(dropped) < limit:
            dropped.append(normalized)
    return accepted, dropped


def _normalize_sample(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "identifier": row.get("identifier"),
        "resolution_status": row.get("resolution_status"),
        "accepted_callee_id": row.get("accepted_callee_id"),
        "provenance": row.get("provenance"),
        "drop_reason": row.get("drop_reason"),
        "candidate_count": int(row.get("candidate_count") or 0),
        "callee_kind": row.get("callee_kind"),
        "line_span": (
            [row.get("call_start_byte"), row.get("call_end_byte")]
            if row.get("call_start_byte") is not None
            and row.get("call_end_byte") is not None
            else None
        ),
        "ordinal": int(row.get("call_ordinal") or 0),
    }


def _totals(rows: list[dict[str, Any]]) -> dict[str, int]:
    eligible = len(rows)
    accepted = sum(1 for row in rows if row.get("resolution_status") == "accepted")
    dropped = eligible - accepted
    return {
        "eligible": eligible,
        "accepted": accepted,
        "dropped": dropped,
    }


def _sorted_bucket_items(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, dict):
        return []
    items: list[dict[str, object]] = []
    for key, value in raw.items():
        count = int(value or 0)
        if count <= 0:
            continue
        items.append({"name": str(key), "count": count})
    items.sort(key=lambda item: (-int(item["count"]), str(item["name"])))
    return items


def _sorted_histogram_items(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, dict):
        return []
    items: list[dict[str, object]] = []
    for key, value in raw.items():
        count = int(value or 0)
        if count <= 0:
            continue
        try:
            bucket = int(str(key))
        except ValueError:
            continue
        items.append({"candidate_count": bucket, "count": count})
    items.sort(key=lambda item: int(item["candidate_count"]))
    return items


__all__ = ["render", "REDUCER_META"]
