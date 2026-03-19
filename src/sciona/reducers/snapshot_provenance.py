# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Snapshot provenance reducer."""

from __future__ import annotations

from .helpers.shared.context import current_artifact_connection, fallback_artifact_connection
from .helpers.shared.connection import require_connection
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .metadata import ReducerMeta
from ..data_storage.core_db import read_ops as core_read
from ..data_storage.artifact_db.reporting import read_status as artifact_read_status

REDUCER_META = ReducerMeta(
    reducer_id="snapshot_provenance",
    category="orientation",
    placeholder="SNAPSHOT_PROVENANCE",
    summary="Shows committed snapshot identity and freshness metadata. Use to verify "
    "what snapshot SCIONA results are based on before structural reasoning. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="snapshot_provenance reducer"
    )
    row = core_read.latest_committed_snapshot(conn)
    if not row:
        raise ValueError("snapshot_provenance requires a committed snapshot.")
    selected_snapshot_id = str(row["snapshot_id"])
    body = {
        "payload_kind": "summary",
        "snapshot_id": selected_snapshot_id,
        "created_at": row.get("created_at"),
        "structural_hash": row.get("structural_hash"),
        "git_commit_sha": core_read.snapshot_git_commit_sha(conn, selected_snapshot_id),
        "artifact_available": False,
        "artifact_rebuild_consistent": None,
    }

    artifact_conn = current_artifact_connection()
    owns_connection = False
    if artifact_conn is None:
        artifact_conn = fallback_artifact_connection(repo_root)
        owns_connection = artifact_conn is not None
    if artifact_conn is not None:
        body["artifact_available"] = True
        body["artifact_rebuild_consistent"] = (
            artifact_read_status.rebuild_consistent_for_snapshot(
                artifact_conn,
                snapshot_id=selected_snapshot_id,
            )
        )
    if owns_connection and artifact_conn is not None:
        artifact_conn.close()
    return render_json_payload(body)
