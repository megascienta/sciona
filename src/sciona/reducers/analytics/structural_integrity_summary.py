# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Structural integrity diagnostics reducer."""

from __future__ import annotations

from ...data_storage.core_db import read_ops as core_read
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="structural_integrity_summary",
    category="analytics",
    scope="codebase",
    placeholders=("STRUCTURAL_INTEGRITY_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Structural integrity diagnostics over committed SCI facts. "
    "Use to detect duplicates, lexical orphans, and inheritance-cycle anomalies before downstream reasoning. "
    "Scope: codebase-level. Payload kind: summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    top_k: int = 25,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="structural_integrity_summary reducer"
    )
    limit = _normalize_limit(top_k)
    duplicates = core_read.duplicate_qualified_names(conn, snapshot_id, limit=limit)
    lexical_orphans = core_read.lexical_orphans(conn, snapshot_id, limit=limit)
    inheritance_cycles = core_read.inheritance_cycles(conn, snapshot_id, limit=limit)
    file_distribution = core_read.language_file_node_distribution(conn, snapshot_id)
    low_node_by_language: dict[str, dict[str, int | float | bool]] = {}
    for row in file_distribution:
        language = str(row.get("language") or "")
        if not language:
            continue
        bucket = low_node_by_language.setdefault(
            language, {"files": 0, "low_node_files_leq_1": 0}
        )
        bucket["files"] = int(bucket.get("files") or 0) + 1
        if int(row.get("node_count") or 0) <= 1:
            bucket["low_node_files_leq_1"] = int(bucket.get("low_node_files_leq_1") or 0) + 1
    for bucket in low_node_by_language.values():
        files = int(bucket.get("files") or 0)
        low = int(bucket.get("low_node_files_leq_1") or 0)
        ratio = (low / files) if files > 0 else None
        warning = bool(files >= 200 and ratio is not None and ratio >= 0.60)
        bucket["low_node_ratio"] = ratio
        bucket["inflation_warning"] = warning
    low_node_totals_files = sum(int(v.get("files") or 0) for v in low_node_by_language.values())
    low_node_totals = sum(
        int(v.get("low_node_files_leq_1") or 0) for v in low_node_by_language.values()
    )
    low_node_totals_ratio = (
        (low_node_totals / low_node_totals_files) if low_node_totals_files > 0 else None
    )
    low_node_totals_warning = bool(
        low_node_totals_files >= 200
        and low_node_totals_ratio is not None
        and low_node_totals_ratio >= 0.60
    )
    body = {
        "payload_kind": "summary",
        "top_k": limit,
        "integrity_ok": not duplicates and not lexical_orphans and not inheritance_cycles,
        "duplicate_qualified_names": duplicates,
        "duplicate_qualified_name_count": len(duplicates),
        "lexical_orphans": lexical_orphans,
        "lexical_orphan_count": len(lexical_orphans),
        "inheritance_cycles": inheritance_cycles,
        "inheritance_cycle_count": len(inheritance_cycles),
        "low_node_file_diagnostics": {
            "by_language": low_node_by_language,
            "totals": {
                "files": low_node_totals_files,
                "low_node_files_leq_1": low_node_totals,
                "low_node_ratio": low_node_totals_ratio,
                "inflation_warning": low_node_totals_warning,
            },
            "zero_node_files_observed": 0,
            "zero_node_files_note": "Not observable from indexed files; files without nodes are not materialized in node_instances.",
        },
    }
    return render_json_payload(body)


def _normalize_limit(top_k: int) -> int:
    value = int(top_k)
    if value <= 0:
        raise ValueError("structural_integrity_summary top_k must be positive.")
    return value


__all__ = ["render", "REDUCER_META"]
