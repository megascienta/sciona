# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.common.transactions import transaction
from sciona.data_storage.common.sql_utils import validate_sql_identifier


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


def test_validate_sql_identifier_rejects_unsafe_savepoint() -> None:
    with pytest.raises(ValueError):
        validate_sql_identifier("bad;DROP", kind="savepoint")
