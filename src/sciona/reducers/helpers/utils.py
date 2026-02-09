# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer helpers."""

from __future__ import annotations

from collections import Counter

from ...data_storage.core_db import read_ops as core_read


def top_modules(counter: Counter, *, limit: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]


def require_latest_committed_snapshot(
    conn, snapshot_id: str, *, reducer_name: str = "Reducer"
) -> None:
    committed_ids = core_read.list_committed_snapshots(conn)
    if not committed_ids:
        raise ValueError(f"{reducer_name} requires a committed snapshot.")
    if len(committed_ids) != 1:
        raise ValueError(
            f"{reducer_name} requires exactly one committed snapshot. "
            "Run `sciona build` on clean HEAD."
        )
    if snapshot_id != committed_ids[0]:
        raise ValueError(
            f"{reducer_name} requires the committed snapshot selected by build."
        )
