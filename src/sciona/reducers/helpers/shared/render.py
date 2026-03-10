# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer rendering helpers."""

from __future__ import annotations

def require_connection(conn):
    if conn is None:
        raise ValueError("Reducer requires an open database connection.")
    return conn


def render_json_payload(payload: object) -> object:
    return payload
