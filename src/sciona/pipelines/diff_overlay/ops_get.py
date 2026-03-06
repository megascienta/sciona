# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dirty-worktree diff overlay helpers for reducer payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ...data_storage.artifact_db import diff_overlay as overlay_store
from ...data_storage.artifact_db import diff_overlay_calls as overlay_call_store
from ...data_storage.artifact_db import diff_overlay_summary as overlay_summary_store
from ...data_storage.core_db import read_ops as core_read
from ...reducers.helpers.render import render_json_payload
from ...runtime import git as git_ops
from ...runtime import time as runtime_time
from ...runtime.errors import GitError
from ...runtime.logging import get_logger

from .affection import extract_scope_hint, scoped_affection
from .compute import compute_overlay_rows, worktree_fingerprint
from .patch import apply_overlay_to_payload, parse_json_fenced
from .ops_sort import rows_to_payload
from .schema import validate_diff_payload
from .types import OverlayPayload

logger = get_logger(__name__)

_OVERLAY_PROFILE: dict[str, dict[str, object]] = {
    "snapshot_provenance": {
        "supports_patch": False,
        "scope_type": "unknown",
        "affected_by": [],
    },
    "structural_index": {
        "supports_patch": True,
        "scope_type": "codebase",
        "affected_by": ["nodes", "edges"],
    },
    "module_overview": {
        "supports_patch": True,
        "scope_type": "module",
        "affected_by": ["nodes", "edges"],
    },
    "callable_overview": {
        "supports_patch": True,
        "scope_type": "callable",
        "affected_by": ["nodes"],
    },
    "classifier_overview": {
        "supports_patch": True,
        "scope_type": "classifier",
        "affected_by": ["nodes"],
    },
    "file_outline": {
        "supports_patch": True,
        "scope_type": "file",
        "affected_by": ["nodes"],
    },
    "dependency_edges": {
        "supports_patch": True,
        "scope_type": "module",
        "affected_by": ["edges"],
    },
    "symbol_lookup": {
        "supports_patch": True,
        "scope_type": "query",
        "affected_by": ["nodes"],
    },
    "symbol_references": {
        "supports_patch": True,
        "scope_type": "query",
        "affected_by": ["nodes"],
    },
    "callsite_index": {
        "supports_patch": True,
        "scope_type": "callable",
        "affected_by": ["calls"],
    },
    "classifier_call_graph_summary": {
        "supports_patch": True,
        "scope_type": "classifier",
        "affected_by": ["calls"],
    },
    "module_call_graph_summary": {
        "supports_patch": True,
        "scope_type": "module",
        "affected_by": ["calls"],
    },
    "fan_summary": {
        "supports_patch": True,
        "scope_type": "fan",
        "affected_by": ["calls", "edges"],
    },
    "hotspot_summary": {
        "supports_patch": True,
        "scope_type": "codebase",
        "affected_by": ["nodes", "edges"],
    },
    "classifier_inheritance": {
        "supports_patch": False,
        "scope_type": "classifier",
        "affected_by": [],
    },
    "callable_source": {
        "supports_patch": False,
        "scope_type": "callable",
        "affected_by": [],
    },
    "concatenated_source": {
        "supports_patch": False,
        "scope_type": "unknown",
        "affected_by": [],
    },
}

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
    snapshot_commit = core_read.snapshot_git_commit_sha(core_conn, snapshot_id)
    if not snapshot_commit:
        return None
    base_commit = snapshot_commit
    base_commit_strategy = "snapshot"
    head_commit = None
    merge_base = None
    warnings: list[str] = []
    try:
        git_ops.run_git(["rev-parse", base_commit], repo_root)
    except GitError:
        warnings.append("snapshot_commit_missing")
        base_commit = "HEAD"
        base_commit_strategy = "snapshot_missing"
    try:
        head_commit = git_ops.head_sha(repo_root)
    except GitError:
        head_commit = None
    if head_commit and base_commit != head_commit:
        try:
            merge_base = git_ops.merge_base(repo_root, base_commit, head_commit)
            if merge_base:
                base_commit = merge_base
                base_commit_strategy = "merge_base"
        except GitError:
            warnings.append("merge_base_failed")
            base_commit = head_commit
            base_commit_strategy = "head_fallback"
        if base_commit != head_commit and base_commit_strategy != "merge_base":
            logger.warning(
                "Diff overlay base commit %s differs from HEAD %s; "
                "overlay includes branch divergence.",
                base_commit,
                head_commit,
            )
            warnings.append("base_commit_differs_from_head")
    git_cache: dict[tuple[Path, tuple[str, ...], str | None], str] = {}
    worktree_hash = worktree_fingerprint(repo_root, base_commit, cache=git_cache)
    if not overlay_bundle_exists(artifact_conn, snapshot_id, worktree_hash):
        rows, call_rows, summary, change_warnings = compute_overlay_rows(
            repo_root=repo_root,
            snapshot_id=snapshot_id,
            base_commit=base_commit,
            core_conn=core_conn,
            artifact_conn=artifact_conn,
            worktree_hash=worktree_hash,
            git_cache=git_cache,
        )
        warnings.extend(change_warnings)
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
    return rows_to_payload(
        worktree_hash,
        snapshot_commit=snapshot_commit,
        base_commit=base_commit,
        base_commit_strategy=base_commit_strategy,
        head_commit=head_commit,
        merge_base=merge_base,
        rows=rows,
        call_rows=call_rows,
        summary=summary,
        warnings=warnings,
    )

def _overlay_reason(warnings: list[str]) -> str:
    if "artifact_db_missing" in warnings:
        return "artifact_db_missing"
    if "overlay_unavailable" in warnings:
        return "overlay_unavailable"
    return "overlay_unavailable"

def overlay_bundle_exists(artifact_conn, snapshot_id: str, worktree_hash: str) -> bool:
    if overlay_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        return True
    if overlay_call_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        return True
    if overlay_summary_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        return True
    return False
