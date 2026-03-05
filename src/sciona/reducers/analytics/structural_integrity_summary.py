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
    }
    return render_json_payload(body)


def _normalize_limit(top_k: int) -> int:
    value = int(top_k)
    if value <= 0:
        raise ValueError("structural_integrity_summary top_k must be positive.")
    return value


__all__ = ["render", "REDUCER_META"]
