# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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
from ...runtime import time as runtime_time
from ...runtime.errors import GitError
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
    snapshot_commit = core_read.snapshot_git_commit_sha(core_conn, snapshot_id)
    if not snapshot_commit:
        return None
    base_commit = snapshot_commit
    head_commit = None
    merge_base = None
    warnings: list[str] = []
    try:
        git_ops.run_git(["rev-parse", base_commit], repo_root)
    except GitError:
        warnings.append("snapshot_commit_missing")
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
        warnings.append("base_commit_differs_from_head")
        try:
            merge_base = git_ops.merge_base(repo_root, base_commit, head_commit)
            base_commit = merge_base
        except GitError:
            warnings.append("merge_base_failed")
            base_commit = head_commit
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
        head_commit=head_commit,
        merge_base=merge_base,
        rows=rows,
        call_rows=call_rows,
        summary=summary,
        warnings=warnings,
    )


def apply_overlay_to_text(
    text: str,
    overlay: Optional[OverlayPayload],
    *,
    snapshot_id: str,
    conn,
    strict: bool = False,
    reducer_id: str | None = None,
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
    projection = str(payload.get("projection", "")).strip().lower()
    projection_version = payload.get("projection_version")
    warnings = list(overlay.warnings)
    if patched_projection is False:
        warnings.append("projection_not_patched")
    if projection in _SUMMARY_PROJECTIONS and overlay.summary is None:
        warnings.append("summary_missing")
    patched_detail = _patched_detail(projection, patched_projection)
    diff_payload = {
        "version": 1,
        "worktree_hash": overlay.worktree_hash,
        "snapshot_commit": overlay.snapshot_commit,
        "base_commit": overlay.base_commit,
        "head_commit": overlay.head_commit,
        "merge_base": overlay.merge_base,
        "reducer_id": reducer_id,
        "snapshot_id": snapshot_id,
        "projection": projection or None,
        "projection_version": projection_version,
        "nodes": overlay.nodes,
        "edges": overlay.edges,
        "calls": overlay.calls,
        "summary": overlay.summary,
        "patched": patched_detail,
        "coverage": _coverage_detail(patched_detail, overlay),
        "warnings": warnings,
    }
    schema_warnings = _validate_diff_payload(diff_payload)
    if schema_warnings:
        diff_payload["warnings"].extend(schema_warnings)
    patched["_diff"] = diff_payload
    return render_json_payload(patched)


def attach_unavailable_overlay(
    text: str,
    *,
    snapshot_id: str,
    reducer_id: str | None,
    warnings: list[str],
) -> str:
    payload = parse_json_fenced(text)
    if payload is None or "_diff" in payload:
        return text
    projection = str(payload.get("projection", "")).strip().lower()
    diff_payload = {
        "version": 1,
        "worktree_hash": None,
        "snapshot_commit": None,
        "base_commit": None,
        "head_commit": None,
        "merge_base": None,
        "reducer_id": reducer_id,
        "snapshot_id": snapshot_id,
        "projection": projection or None,
        "projection_version": payload.get("projection_version"),
        "nodes": None,
        "edges": None,
        "calls": None,
        "summary": None,
        "patched": "none",
        "coverage": "none",
        "warnings": list(warnings),
    }
    payload["_diff"] = diff_payload
    return render_json_payload(payload)


_NODE_PROJECTIONS = {
    "structural_index",
    "module_overview",
    "callable_overview",
    "class_overview",
    "file_outline",
    "module_file_map",
    "dependency_edges",
    "import_references",
    "importers_index",
    "symbol_lookup",
    "symbol_references",
}

_SUMMARY_PROJECTIONS = {
    "call_graph",
    "callsite_index",
    "class_call_graph",
    "module_call_graph",
    "fan_summary",
    "hotspot_summary",
}


def _patched_detail(projection: str, patched_projection: bool) -> dict[str, object]:
    if not patched_projection:
        return {
            "projection": False,
            "nodes": False,
            "edges": False,
            "calls": False,
            "summary": False,
            "reasons": ["projection_not_supported"],
        }
    return {
        "projection": True,
        "nodes": projection in _NODE_PROJECTIONS,
        "edges": projection in _NODE_PROJECTIONS,
        "calls": False,
        "summary": projection in _SUMMARY_PROJECTIONS,
        "reasons": [],
    }


def _coverage_detail(
    patched_detail: dict[str, object], overlay: OverlayPayload
) -> dict[str, str]:
    def _coverage(flag: bool, data: dict[str, list[dict[str, object]]] | None) -> str:
        if not flag:
            return "none"
        if not data:
            return "none"
        if not any(data.values()):
            return "none"
        return "partial"

    nodes = _coverage(bool(patched_detail.get("nodes")), overlay.nodes)
    edges = _coverage(bool(patched_detail.get("edges")), overlay.edges)
    calls = _coverage(bool(patched_detail.get("calls")), overlay.calls)
    summary = "partial" if patched_detail.get("summary") and overlay.summary else "none"
    return {
        "nodes": nodes,
        "edges": edges,
        "calls": calls,
        "summary": summary,
    }


def _validate_diff_payload(diff: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    if not isinstance(diff.get("version"), int):
        warnings.append("schema:version_not_int")
    if not isinstance(diff.get("worktree_hash"), str):
        warnings.append("schema:worktree_hash_not_str")
    for key in ("nodes", "edges", "calls"):
        value = diff.get(key)
        if not isinstance(value, dict):
            warnings.append(f"schema:{key}_not_dict")
            continue
        for diff_kind, entries in value.items():
            if diff_kind not in {"add", "remove", "modify"}:
                warnings.append(f"schema:{key}_invalid_kind:{diff_kind}")
                continue
            if not isinstance(entries, list):
                warnings.append(f"schema:{key}_{diff_kind}_not_list")
    summary = diff.get("summary")
    if summary is not None and not isinstance(summary, dict):
        warnings.append("schema:summary_not_dict")
    patched = diff.get("patched")
    if not isinstance(patched, dict):
        warnings.append("schema:patched_not_dict")
    coverage = diff.get("coverage")
    if not isinstance(coverage, dict):
        warnings.append("schema:coverage_not_dict")
    return warnings


__all__ = [
    "apply_overlay_to_text",
    "get_overlay",
]
