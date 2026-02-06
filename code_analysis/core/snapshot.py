"""Snapshot metadata capture helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from ...runtime import git as git_ops
from ...runtime.time import utc_now


@dataclass
class Snapshot:
    snapshot_id: str
    created_at: str
    source: str
    git_commit_sha: str
    git_commit_time: str
    git_branch: str


def create_snapshot(repo_root: Path, source: str = "scan") -> Snapshot:
    """Capture git metadata for the current ingest output."""
    meta = git_ops.commit_meta(repo_root)
    created_at = utc_now()
    snapshot_id = uuid.uuid4().hex
    return Snapshot(
        snapshot_id=snapshot_id,
        created_at=created_at,
        source=source,
        git_commit_sha=meta["git_commit_sha"],
        git_commit_time=meta["git_commit_time"],
        git_branch=meta["git_branch"],
    )


def persist_snapshot(
    conn,
    snapshot: Snapshot,
    structural_hash: str,
    is_committed: bool,
    *,
    store,
) -> None:
    """Persist snapshot metadata after successful ingestion."""
    store.insert_snapshot(
        conn,
        snapshot_id=snapshot.snapshot_id,
        created_at=snapshot.created_at,
        source=snapshot.source,
        structural_hash=structural_hash,
        git_commit_sha=snapshot.git_commit_sha,
        git_commit_time=snapshot.git_commit_time,
        git_branch=snapshot.git_branch,
        is_committed=is_committed,
    )
