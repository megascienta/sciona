# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

from sciona.data_storage.schema_utils import ensure_schema


def test_ensure_schema_executes_statements(tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "db.sqlite")
    ensure_schema(conn, ["CREATE TABLE example (id TEXT PRIMARY KEY)"])
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='example'"
    ).fetchone()
    assert row is not None
    conn.close()
