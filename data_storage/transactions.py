# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Transaction helpers for coordinated persistence."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from uuid import uuid4

import sqlite3


def _savepoint_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    use_savepoint = conn.in_transaction
    savepoint = _savepoint_name("tx_guard")
    if use_savepoint:
        conn.execute(f"SAVEPOINT {savepoint}")
    else:
        conn.execute("BEGIN")
    try:
        yield conn
        if use_savepoint:
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            conn.commit()
    except Exception:
        if use_savepoint:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        else:
            conn.rollback()
        raise
