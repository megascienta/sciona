"""Dirty-worktree diff overlay helpers for reducer payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...data_storage.artifact_db import diff_overlay as overlay_store
from ...data_storage.artifact_db import diff_overlay_calls as overlay_call_store
from ...data_storage.artifact_db import diff_overlay_summary as overlay_summary_store
from ...data_storage.core_db import read_ops as core_read
from ...reducers.helpers.render import render_json_payload
from ...runtime import git as git_ops
from ...runtime.errors import GitError
from ...runtime import time as runtime_time
from ...runtime.logging import get_logger

from .compute import compute_overlay_rows, worktree_fingerprint
from .patch import apply_overlay_to_payload, parse_json_fenced
from .store import overlay_bundle_exists, rows_to_payload
from .types import OverlayPayload

logger = get_logger(__name__)


def get_overlay(
    *,
    repo_root: Path,
    snapshot_id: str,
    core_conn,
    artifact_conn,
) -> Optional[OverlayPayload]:
    if artifact_conn is None:
        return None
    if not git_ops.is_worktree_dirty(repo_root):
        return None
    base_commit = core_read.snapshot_git_commit_sha(core_conn, snapshot_id)
    if not base_commit:
        return None
    head_commit = None
    try:
        git_ops.run_git(["rev-parse", base_commit], repo_root)
    except GitError:
        base_commit = "HEAD"
    try:
        head_commit = git_ops.head_sha(repo_root)
    except GitError:
        head_commit = None
    if head_commit and base_commit != head_commit:
        logger.warning(
            "Diff overlay base commit %s differs from HEAD %s; "
            "overlay includes branch divergence.",
            base_commit,
            head_commit,
        )
        try:
            base_commit = git_ops.merge_base(repo_root, base_commit, head_commit)
        except GitError:
            base_commit = head_commit
    git_cache: dict[tuple[Path, tuple[str, ...], str | None], str] = {}
    worktree_hash = worktree_fingerprint(repo_root, base_commit, cache=git_cache)
    if not overlay_bundle_exists(artifact_conn, snapshot_id, worktree_hash):
        rows, call_rows, summary = compute_overlay_rows(
            repo_root=repo_root,
            snapshot_id=snapshot_id,
            base_commit=base_commit,
            core_conn=core_conn,
            artifact_conn=artifact_conn,
            worktree_hash=worktree_hash,
            git_cache=git_cache,
        )
        overlay_store.insert_overlay_rows(artifact_conn, rows)
        overlay_call_store.insert_call_rows(artifact_conn, call_rows)
        if summary is not None:
            overlay_summary_store.insert_summary(
                artifact_conn,
                snapshot_id=snapshot_id,
                worktree_hash=worktree_hash,
                summary=summary,
                created_at=runtime_time.utc_now(),
            )
        artifact_conn.commit()
    rows = overlay_store.fetch_overlay_rows(artifact_conn, snapshot_id, worktree_hash)
    call_rows = overlay_call_store.fetch_call_rows(
        artifact_conn, snapshot_id, worktree_hash
    )
    summary = overlay_summary_store.fetch_summary(
        artifact_conn, snapshot_id, worktree_hash
    )
    if not rows and not call_rows and not summary:
        return None
    return rows_to_payload(worktree_hash, rows, call_rows, summary)


def apply_overlay_to_text(
    text: str,
    overlay: Optional[OverlayPayload],
    *,
    snapshot_id: str,
    conn,
    strict: bool = False,
) -> str:
    if not overlay:
        return text
    payload = parse_json_fenced(text)
    if payload is None:
        if strict:
            raise ValueError("Reducer payload must be JSON.")
        return text
    patched, patched_projection = apply_overlay_to_payload(
        payload, overlay, snapshot_id=snapshot_id, conn=conn
    )
    patched["_diff"] = {
        "version": 1,
        "worktree_hash": overlay.worktree_hash,
        "nodes": overlay.nodes,
        "edges": overlay.edges,
        "calls": overlay.calls,
        "summary": overlay.summary,
        "patched": patched_projection,
    }
    return render_json_payload(patched)


__all__ = ["OverlayPayload", "apply_overlay_to_text", "get_overlay"]
