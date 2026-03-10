# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Snapshot preparation helpers for ingestion and artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from ....runtime import git as git_ops
from ...core.normalize.model import FileRecord, FileSnapshot


def _ensure_repo_contained(repo_root: Path, record: FileRecord) -> None:
    resolved_repo = repo_root.resolve()
    resolved_path = record.path.resolve()
    resolved_path.relative_to(resolved_repo)


def prepare_file_snapshots(
    repo_root: Path,
    records: List[FileRecord],
    *,
    on_error: Optional[Callable[[Path, Exception], None]] = None,
) -> List[FileSnapshot]:
    """Build FileSnapshot entries with git blob and line metadata."""
    snapshots: List[FileSnapshot] = []
    blob_shas = git_ops.blob_sha_batch(
        repo_root, [record.relative_path for record in records]
    )
    for record in records:
        _ensure_repo_contained(repo_root, record)
        blob = blob_shas.get(record.relative_path) or git_ops.blob_sha(
            repo_root, record.relative_path
        )
        size = record.path.stat().st_size
        line_count = count_lines_fast(record.path, on_error=on_error)
        snapshots.append(
            FileSnapshot(
                record=record,
                file_id="",
                blob_sha=blob,
                size=size,
                line_count=line_count,
                content=None,
            )
        )
    return snapshots


def count_lines_fast(
    path: Path,
    *,
    on_error: Optional[Callable[[Path, Exception], None]] = None,
) -> int:
    try:
        with path.open("rb") as handle:
            count = sum(1 for _ in handle)
        return max(1, count)
    except (OSError, IOError) as exc:
        if on_error is not None:
            on_error(path, exc)
        return 1
