"""Persistence encoding helpers."""

from __future__ import annotations


def bool_to_int(value: bool) -> int:
    return 1 if value else 0
