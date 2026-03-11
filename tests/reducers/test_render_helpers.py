# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import sqlite3

import pytest

from sciona.reducers.helpers.shared.render import (
    render_json_payload,
    require_connection,
)
from sciona.reducers.helpers.shared.utils import require_latest_committed_snapshot
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.data_storage.core_db import write_ops as core_write


def test_require_connection_raises_for_none() -> None:
    with pytest.raises(ValueError, match="open database connection"):
        require_connection(None)


def test_require_connection_returns_same_connection() -> None:
    sentinel = object()
    assert require_connection(sentinel) is sentinel


def test_render_json_payload_returns_structured_payload() -> None:
    rendered = render_json_payload({"b": 2, "a": {"d": 4, "c": 3}})
    assert rendered == {"b": 2, "a": {"d": 4, "c": 3}}


def test_require_latest_committed_snapshot_rejects_missing_and_multiple_committed(
    monkeypatch, tmp_path
) -> None:
    db_path = tmp_path / "core.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    with pytest.raises(ValueError, match="requires a committed snapshot"):
        require_latest_committed_snapshot(conn, "snap_missing", reducer_name="Reducer")

    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_old",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash-old",
        is_committed=True,
        git_commit_time="2024-01-01T00:00:00Z",
    )
    conn.commit()
    monkeypatch.setattr(
        "sciona.reducers.helpers.shared.utils.core_read.list_committed_snapshots",
        lambda _conn: ["snap_new", "snap_old"],
    )
    with pytest.raises(ValueError, match="exactly one committed snapshot"):
        require_latest_committed_snapshot(conn, "snap_old", reducer_name="Reducer")
    conn.close()


def test_require_latest_committed_snapshot_accepts_selected_committed_snapshot(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_only",
        created_at="2024-01-02T00:00:00Z",
        source="test",
        structural_hash="hash-only",
        is_committed=True,
        git_commit_time="2024-01-02T00:00:00Z",
    )
    conn.commit()

    require_latest_committed_snapshot(conn, "snap_only", reducer_name="Reducer")
    with pytest.raises(ValueError, match="committed snapshot selected by build"):
        require_latest_committed_snapshot(conn, "snap_other", reducer_name="Reducer")
    conn.close()
