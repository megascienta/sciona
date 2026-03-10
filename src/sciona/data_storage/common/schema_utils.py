# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Schema helper utilities."""

from __future__ import annotations

import sqlite3
from typing import Iterable


def ensure_schema(conn: sqlite3.Connection, statements: Iterable[str]) -> None:
    cur = conn.cursor()
    for statement in statements:
        cur.execute(statement)
