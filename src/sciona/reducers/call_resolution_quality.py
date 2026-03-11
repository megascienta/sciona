# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Aggregated call-resolution quality diagnostics."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List

from ..data_storage.core_db import read_ops as core_read
from ..pipelines.diff_overlay.patching.analytics import patch_call_resolution_quality
from .helpers.shared import queries
from .helpers.artifact.graph_edges import artifact_db_available
from .helpers.artifact.reporting import load_callsite_caller_status_counts
from .helpers.shared.context import current_overlay_payload
from .helpers.shared.connection import require_connection
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="call_resolution_quality",
    category="diagnostic",
    placeholder="CALL_RESOLUTION_QUALITY",
    summary="Aggregated call-resolution quality diagnostics derived from callsite telemetry. "
    "Use to understand accepted vs dropped callsite distribution and dominant drop reasons. ",
    anomaly_detector=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    language: str | None = None,
    limit: int | str | None = 10,
    compact: bool | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="call_resolution_quality reducer"
    )
    artifact_available = artifact_db_available(repo_root) if repo_root else False
    normalized_language = _normalize_language(language)
    limit_value = _normalize_limit(limit)
    rows = (
        load_callsite_caller_status_counts(
            repo_root=repo_root,
            snapshot_id=snapshot_id,
        )
        if artifact_available and repo_root is not None
        else []
    )

    caller_lookup = core_read.caller_node_metadata_map(conn, snapshot_id)
    module_lookup = queries.module_id_lookup(conn, snapshot_id)
    module_filter_ids = _resolve_module_filter_ids(conn, snapshot_id, module_id)

    filtered = []
    for row in rows:
        caller_id = str(row.get("caller_id") or "")
        if not caller_id:
            continue
        meta = caller_lookup.get(caller_id)
        if not meta:
            continue
        row_module = module_lookup.get(caller_id)
        row_language = str(meta.get("language") or "")
        if module_filter_ids is not None and row_module not in module_filter_ids:
            continue
        if normalized_language and row_language != normalized_language:
            continue
        filtered.append((row, meta, row_module))

    totals = {"eligible": 0, "accepted": 0, "dropped": 0}
    drop_reasons: Counter[str] = Counter()
    by_language = defaultdict(lambda: {"eligible": 0, "accepted": 0, "dropped": 0})
    by_module = defaultdict(lambda: {"eligible": 0, "accepted": 0, "dropped": 0})
    by_caller = defaultdict(
        lambda: {
            "eligible": 0,
            "accepted": 0,
            "dropped": 0,
            "qualified_name": "",
            "language": "",
            "module_qualified_name": "",
            "file_path": "",
        }
    )

    for row, meta, row_module in filtered:
        status = str(row.get("resolution_status") or "")
        site_count = int(row.get("site_count") or 0)
        caller_id = str(row.get("caller_id") or "")
        language_value = str(meta.get("language") or "")
        qualified_name = str(meta.get("qualified_name") or "")
        file_path = str(meta.get("file_path") or "")
        module_value = row_module or ""

        totals["eligible"] += site_count
        by_language[language_value]["eligible"] += site_count
        by_module[module_value]["eligible"] += site_count

        caller_entry = by_caller[caller_id]
        caller_entry["eligible"] += site_count
        caller_entry["qualified_name"] = qualified_name
        caller_entry["language"] = language_value
        caller_entry["module_qualified_name"] = module_value
        caller_entry["file_path"] = file_path

        if status == "accepted":
            totals["accepted"] += site_count
            by_language[language_value]["accepted"] += site_count
            by_module[module_value]["accepted"] += site_count
            caller_entry["accepted"] += site_count
        elif status == "dropped":
            totals["dropped"] += site_count
            by_language[language_value]["dropped"] += site_count
            by_module[module_value]["dropped"] += site_count
            caller_entry["dropped"] += site_count
            reason = str(row.get("drop_reason") or "")
            if reason:
                drop_reasons[reason] += site_count

    body = {
        "payload_kind": "summary",
        "module_filter": module_id,
        "language_filter": normalized_language,
        "limit": limit_value,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
        "totals": {
            **totals,
            "acceptance_rate": _ratio(totals["accepted"], totals["eligible"]),
        },
        "committed_totals": {
            **totals,
            "acceptance_rate": _ratio(totals["accepted"], totals["eligible"]),
        },
        "overlay_adjusted_totals": {
            **totals,
            "acceptance_rate": _ratio(totals["accepted"], totals["eligible"]),
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
        "drop_reason_counts": _counter_entries(drop_reasons, limit_value),
        "by_language": _metric_entries(by_language, key_name="language", top_k=limit_value),
        "by_module": _metric_entries(
            by_module, key_name="module_qualified_name", top_k=limit_value
        ),
        "by_caller": _caller_entries(by_caller, top_k=limit_value),
    }
    overlay = current_overlay_payload()
    if overlay is not None:
        body = patch_call_resolution_quality(
            body,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
        body["_overlay_applied_by_reducer"] = True
    if compact:
        body = _compact_payload(body)
    return render_json_payload(body)


def _resolve_module_filter_ids(
    conn,
    snapshot_id: str,
    module_id: str | None,
) -> set[str] | None:
    if not module_id:
        return None
    modules = queries.list_modules(conn, snapshot_id)
    selected = {
        str(row.get("qualified_name") or "")
        for row in modules
        if row.get("qualified_name") == module_id or row.get("structural_id") == module_id
    }
    if selected:
        return selected
    raise ValueError(f"Module '{module_id}' not found in snapshot '{snapshot_id}'.")


def _metric_entries(
    mapping: Dict[str, Dict[str, int]],
    *,
    key_name: str,
    top_k: int,
) -> List[dict]:
    entries = []
    for key, counts in mapping.items():
        entries.append(
            {
                key_name: key,
                "eligible": counts["eligible"],
                "accepted": counts["accepted"],
                "dropped": counts["dropped"],
                "acceptance_rate": _ratio(counts["accepted"], counts["eligible"]),
            }
        )
    entries.sort(
        key=lambda item: (
            -int(item.get("eligible") or 0),
            str(item.get(key_name) or ""),
        )
    )
    return entries[:top_k]


def _caller_entries(mapping: Dict[str, Dict[str, object]], top_k: int) -> List[dict]:
    entries = []
    for caller_id, row in mapping.items():
        eligible = int(row.get("eligible") or 0)
        accepted = int(row.get("accepted") or 0)
        dropped = int(row.get("dropped") or 0)
        entries.append(
            {
                "caller_id": caller_id,
                "qualified_name": row.get("qualified_name"),
                "language": row.get("language"),
                "module_qualified_name": row.get("module_qualified_name"),
                "file_path": row.get("file_path"),
                "eligible": eligible,
                "accepted": accepted,
                "dropped": dropped,
                "acceptance_rate": _ratio(accepted, eligible),
            }
        )
    entries.sort(
        key=lambda item: (
            -int(item.get("eligible") or 0),
            str(item.get("qualified_name") or ""),
            str(item.get("caller_id") or ""),
        )
    )
    return entries[:top_k]


def _counter_entries(counter: Counter[str], top_k: int) -> List[dict]:
    rows = [{"name": name, "count": count} for name, count in counter.items()]
    rows.sort(key=lambda item: (-int(item["count"]), str(item["name"])))
    return rows[:top_k]


def _normalize_limit(limit: int | str | None) -> int:
    if limit is None:
        return 10
    value = int(limit)
    if value <= 0:
        raise ValueError("call_resolution_quality limit must be a positive integer.")
    return min(value, 100)


def _compact_payload(payload: Dict[str, object]) -> Dict[str, object]:
    compact_payload = dict(payload)
    compact_payload["payload_kind"] = "compact_summary"
    compact_payload["drop_reasons_preview"] = _preview_block(
        payload.get("drop_reason_counts", []) or []
    )
    compact_payload["language_preview"] = _preview_block(payload.get("by_language", []) or [])
    compact_payload["module_preview"] = _preview_block(payload.get("by_module", []) or [])
    compact_payload["caller_preview"] = _preview_block(payload.get("by_caller", []) or [])
    compact_payload.pop("drop_reason_counts", None)
    compact_payload.pop("by_language", None)
    compact_payload.pop("by_module", None)
    compact_payload.pop("by_caller", None)
    return compact_payload


def _preview_block(entries: List[dict]) -> Dict[str, object]:
    return {
        "count": len(entries),
        "entries": entries,
        "truncated": False,
    }


def _normalize_language(language: str | None) -> str | None:
    if language is None:
        return None
    value = str(language).strip().lower()
    if not value:
        return None
    if value not in {"python", "typescript", "javascript", "java"}:
        raise ValueError(
            "call_resolution_quality language must be one of: "
            "python, typescript, javascript, java."
        )
    return value


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)
