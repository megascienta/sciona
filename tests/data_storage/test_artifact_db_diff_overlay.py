# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

from sciona.data_storage.artifact_db.overlay import diff_overlay
from sciona.data_storage.artifact_db.schema import ensure_schema


def test_diff_overlay_round_trip(tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "artifact.db")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    rows = [
        {
            "snapshot_id": "snap",
            "worktree_hash": "hash",
            "structural_id": "node_a",
            "node_type": "function",
            "diff_kind": "modified",
            "field": "qualified_name",
            "old_value": "pkg.old",
            "new_value": "pkg.new",
            "created_at": "2026-01-01T00:00:00Z",
        }
    ]
    diff_overlay.insert_overlay_rows(conn, rows)

    assert diff_overlay.overlay_exists(conn, "snap", "hash") is True
    fetched = diff_overlay.fetch_overlay_rows(conn, "snap", "hash")
    assert fetched == [
        {
            "structural_id": "node_a",
            "node_type": "function",
            "diff_kind": "modified",
            "field": "qualified_name",
            "old_value": "pkg.old",
            "new_value": "pkg.new",
        }
    ]

    diff_overlay.clear_overlay(conn, "snap", "hash")
    assert diff_overlay.overlay_exists(conn, "snap", "hash") is False

    diff_overlay.insert_overlay_rows(conn, rows)
    diff_overlay.clear_all(conn)
    assert diff_overlay.overlay_exists(conn, "snap", "hash") is False
    conn.close()
