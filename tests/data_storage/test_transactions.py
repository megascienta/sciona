# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.transactions import transaction


def test_transaction_rolls_back_on_exception(tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "db.sqlite")
    conn.execute("CREATE TABLE items (id TEXT PRIMARY KEY)")

    with pytest.raises(RuntimeError):
        with transaction(conn):
            conn.execute("INSERT INTO items(id) VALUES ('alpha')")
            raise RuntimeError("boom")

    row = conn.execute("SELECT id FROM items").fetchone()
    assert row is None
    conn.close()
