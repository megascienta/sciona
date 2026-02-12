# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer helpers."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
from typing import Optional

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


def line_span_hash(
    repo_root: Optional[Path],
    file_path: Optional[str],
    line_span: Optional[list[int]],
) -> Optional[str]:
    if repo_root is None or not file_path or not line_span:
        return None
    if len(line_span) != 2:
        return None
    start, end = line_span
    if start is None or end is None or start < 1 or end < start:
        return None
    resolved = resolve_repo_file(repo_root, file_path)
    if resolved is None:
        return None
    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = content.splitlines(keepends=True)
    if start > len(lines):
        return None
    segment = "".join(lines[start - 1 : min(end, len(lines))])
    if not segment:
        return None
    return hashlib.sha1(segment.encode("utf-8")).hexdigest()


def resolve_repo_file(
    repo_root: Optional[Path],
    file_path: Optional[str | Path],
) -> Optional[Path]:
    if repo_root is None or not file_path:
        return None
    repo_root = Path(repo_root).resolve()
    candidate = Path(file_path)
    if candidate.is_absolute():
        full_path = candidate
    else:
        full_path = repo_root / candidate
    try:
        resolved = full_path.resolve()
    except FileNotFoundError:
        return None
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None
    if not resolved.is_file():
        return None
    return resolved
