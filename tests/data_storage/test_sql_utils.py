# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.sql_utils import chunked, temp_id_table


def test_chunked_splits_sequences() -> None:
    values = ["a", "b", "c", "d"]
    chunks = list(chunked(values, 2))
    assert chunks == [["a", "b"], ["c", "d"]]


def test_chunked_requires_positive_size() -> None:
    with pytest.raises(ValueError):
        list(chunked(["a"], 0))


def test_temp_id_table_creates_and_drops(tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "db.sqlite")
    with temp_id_table(conn, ["one", "two"]) as table_name:
        rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        assert rows[0] == 2
        exists = conn.execute(
            "SELECT name FROM sqlite_temp_master WHERE name = ?", (table_name,)
        ).fetchone()
        assert exists is not None
    after = conn.execute(
        "SELECT name FROM sqlite_temp_master WHERE name = ?", (table_name,)
    ).fetchone()
    assert after is None
    conn.close()
