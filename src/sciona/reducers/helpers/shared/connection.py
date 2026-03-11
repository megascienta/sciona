# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Connection guard helpers shared by reducers."""

from __future__ import annotations


def require_connection(conn):
    if conn is None:
        raise ValueError("Reducer requires an open database connection.")
    return conn


__all__ = ["require_connection"]
