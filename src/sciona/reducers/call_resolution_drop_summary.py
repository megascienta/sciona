# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Aggregated dropped-callsite diagnostics."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from ..data_storage.artifact_db.reporting import read_reporting as artifact_reporting
from ..data_storage.core_db import read_ops as core_read
from ..runtime.overlay.patching.analytics import (
    patch_call_resolution_drop_summary,
)
from .helpers.shared import queries
from .helpers.shared.context import current_artifact_connection, fallback_artifact_connection
from .helpers.shared.context import current_overlay_payload
from .helpers.shared.render import render_json_payload, require_connection
from .helpers.shared.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="call_resolution_drop_summary",
    category="diagnostic",
    placeholder="CALL_RESOLUTION_DROP_SUMMARY",
    summary="Summarize artifact-layer dropped callsite outcomes by reason, language, "
    "and scope for fast call-resolution triage. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    limit: int | str | None = 10,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="call_resolution_drop_summary reducer"
    )
    limit_value = _normalize_limit(limit)
    artifact_conn = current_artifact_connection()
    owns_connection = False
    if artifact_conn is None and repo_root is not None:
        artifact_conn = fallback_artifact_connection(repo_root)
        owns_connection = artifact_conn is not None

    body = {
        "payload_kind": "summary",
        "limit": limit_value,
        "artifact_available": artifact_conn is not None,
        "edge_source": "artifact_db" if artifact_conn is not None else "none",
        "totals": {
            "eligible": 0,
            "accepted": 0,
            "dropped": 0,
            "drop_rate": None,
        },
        "committed_totals": {
            "eligible": 0,
            "accepted": 0,
            "dropped": 0,
            "drop_rate": None,
        },
        "overlay_adjusted_totals": {
            "eligible": 0,
            "accepted": 0,
            "dropped": 0,
            "drop_rate": None,
        },
        "overlay_delta_totals": {
            "eligible": 0,
            "accepted": 0,
            "dropped": 0,
        },
        "overlay_transition_counts": {
            "accepted_to_dropped": 0,
            "dropped_to_accepted": 0,
        },
        "overlay_drop_reason_delta": [],
        "dropped_by_reason": [],
        "dropped_by_reason_by_language": [],
        "dropped_by_reason_by_scope": {
            "non_tests": [],
            "tests": [],
        },
        "top_callers_by_drop_count": [],
    }
    if artifact_conn is None:
        return render_json_payload(body)

    try:
        status_rows = artifact_reporting.call_site_caller_status_counts(
            artifact_conn,
            snapshot_id=snapshot_id,
        )
        drop_rows = artifact_reporting.call_site_drop_identifier_counts(
            artifact_conn,
            snapshot_id=snapshot_id,
        )
    finally:
        if owns_connection:
            artifact_conn.close()

    caller_lookup = core_read.caller_node_metadata_map(conn, snapshot_id)
    module_lookup = queries.module_id_lookup(conn, snapshot_id)

    totals = {"eligible": 0, "accepted": 0, "dropped": 0}
    top_callers: dict[str, dict[str, object]] = {}
    for row in status_rows:
        count = int(row.get("site_count") or 0)
        status = str(row.get("resolution_status") or "")
        caller_id = str(row.get("caller_id") or "")
        meta = caller_lookup.get(caller_id, {})
        totals["eligible"] += count
        if status == "accepted":
            totals["accepted"] += count
        elif status == "dropped":
            totals["dropped"] += count
            entry = top_callers.setdefault(
                caller_id,
                {
                    "caller_id": caller_id,
                    "qualified_name": str(meta.get("qualified_name") or ""),
                    "language": str(meta.get("language") or ""),
                    "file_path": str(meta.get("file_path") or ""),
                    "module_qualified_name": str(module_lookup.get(caller_id) or ""),
                    "dropped": 0,
                },
            )
            entry["dropped"] = int(entry["dropped"] or 0) + count

    by_reason: Counter[str] = Counter()
    by_language: dict[str, Counter[str]] = defaultdict(Counter)
    by_scope: dict[str, Counter[str]] = {
        "non_tests": Counter(),
        "tests": Counter(),
    }
    for row in drop_rows:
        caller_id = str(row.get("caller_id") or "")
        meta = caller_lookup.get(caller_id, {})
        reason = str(row.get("drop_reason") or "unknown")
        count = int(row.get("site_count") or 0)
        language = str(meta.get("language") or "unknown")
        scope = _scope_bucket(str(meta.get("file_path") or ""))
        by_reason[reason] += count
        by_language[language][reason] += count
        by_scope[scope][reason] += count

    body["totals"] = {
        **totals,
        "drop_rate": _ratio(totals["dropped"], totals["eligible"]),
    }
    body["committed_totals"] = dict(body["totals"])
    body["overlay_adjusted_totals"] = dict(body["totals"])
    body["dropped_by_reason"] = _counter_entries(by_reason, limit_value)
    body["dropped_by_reason_by_language"] = _grouped_counter_entries(
        by_language,
        key_name="language",
        limit=limit_value,
    )
    body["dropped_by_reason_by_scope"] = {
        scope: _counter_entries(counter, limit_value)
        for scope, counter in by_scope.items()
    }
    body["top_callers_by_drop_count"] = _top_callers(top_callers, limit_value)
    overlay = current_overlay_payload()
    if overlay is not None:
        body = patch_call_resolution_drop_summary(
            body,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
        body["_overlay_applied_by_reducer"] = True
    return render_json_payload(body)


def _normalize_limit(limit: int | str | None) -> int:
    if limit is None:
        return 10
    value = int(limit)
    if value <= 0:
        raise ValueError(
            "call_resolution_drop_summary limit must be a positive integer."
        )
    return min(value, 100)


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _counter_entries(counter: Counter[str], limit: int) -> list[dict[str, object]]:
    rows = [{"name": name, "count": count} for name, count in counter.items()]
    rows.sort(key=lambda item: (-int(item["count"]), str(item["name"])))
    return rows[:limit]


def _grouped_counter_entries(
    counters: dict[str, Counter[str]],
    *,
    key_name: str,
    limit: int,
) -> list[dict[str, object]]:
    rows = []
    for key, counter in counters.items():
        total = sum(int(count) for count in counter.values())
        rows.append(
            {
                key_name: key,
                "dropped": total,
                "drop_reasons": _counter_entries(counter, limit),
            }
        )
    rows.sort(key=lambda item: (-int(item["dropped"]), str(item[key_name])))
    return rows[:limit]


def _top_callers(
    mapping: dict[str, dict[str, object]],
    limit: int,
) -> list[dict[str, object]]:
    rows = list(mapping.values())
    rows.sort(
        key=lambda item: (
            -int(item.get("dropped") or 0),
            str(item.get("qualified_name") or ""),
            str(item.get("caller_id") or ""),
        )
    )
    return rows[:limit]


def _scope_bucket(file_path: str) -> str:
    normalized = Path(file_path).as_posix().strip("/")
    if not normalized:
        return "non_tests"
    parts = [part for part in normalized.split("/") if part]
    return "tests" if any(part in {"test", "tests"} for part in parts) else "non_tests"


__all__ = ["render", "REDUCER_META"]
