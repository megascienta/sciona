"""Persistence encoding helpers."""
from __future__ import annotations


def bool_to_int(value: bool) -> int:
    return 1 if value else 0


def int_to_bool(value: int | bool) -> bool:
    return bool(int(value))
