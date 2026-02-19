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
from .schema import validate_diff_payload
from .types import OverlayPayload

logger = get_logger(__name__)

_OVERLAY_PROFILE: dict[str, dict[str, object]] = {
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
    "class_overview": {
        "supports_patch": True,
        "scope_type": "class",
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
    "class_call_graph_summary": {
        "supports_patch": True,
        "scope_type": "class",
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
    "class_inheritance": {
        "supports_patch": False,
        "scope_type": "class",
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


def apply_overlay_to_text(
    text: str,
    overlay: Optional[OverlayPayload],
    *,
    repo_root: Path,
    snapshot_id: str,
    conn,
    strict: bool = False,
    reducer_id: str | None = None,
    diff_mode: str = "full",
) -> str:
    if not overlay:
        return text
    payload = parse_json_fenced(text)
    if payload is None:
        if strict:
            raise ValueError("Reducer payload must be JSON.")
        return text
    patched, patched_projection = apply_overlay_to_payload(
        payload, overlay, snapshot_id=snapshot_id, conn=conn, reducer_id=reducer_id
    )
    projection = _resolve_projection(payload, reducer_id)
    warnings = list(overlay.warnings)
    profile = _OVERLAY_PROFILE.get(projection, None)
    scope_hint = extract_scope_hint(payload, profile)
    affected, affected_by = scoped_affection(overlay, scope_hint, profile)
    if not patched_projection:
        warnings.append("projection_not_patched")
        affected = None
    if profile and not profile.get("supports_patch"):
        warnings.append("projection_not_supported")
        affected = None
    diff_payload = {
        "version": 3,
        "overlay_available": True,
        "overlay_reason": "available",
        "worktree_hash": overlay.worktree_hash,
        "snapshot_commit": overlay.snapshot_commit,
        "base_commit": overlay.base_commit,
        "base_commit_strategy": overlay.base_commit_strategy,
        "head_commit": overlay.head_commit,
        "merge_base": overlay.merge_base,
        "reducer_id": reducer_id,
        "projection": projection or None,
        "scope": scope_hint,
        "affected": affected,
        "affected_by": affected_by,
        "warnings": warnings,
    }
    schema_warnings = validate_diff_payload(diff_payload)
    if schema_warnings:
        diff_payload["warnings"].extend(schema_warnings)
    patched["_diff"] = diff_payload
    return render_json_payload(patched)


def attach_unavailable_overlay(
    text: str,
    *,
    repo_root: Path,
    snapshot_id: str,
    reducer_id: str | None,
    warnings: list[str],
    diff_mode: str = "full",
) -> str:
    payload = parse_json_fenced(text)
    if payload is None or "_diff" in payload:
        return text
    projection = _resolve_projection(payload, reducer_id)
    profile = _OVERLAY_PROFILE.get(projection, None)
    scope_hint = extract_scope_hint(payload, profile)
    diff_payload = {
        "version": 3,
        "overlay_available": False,
        "overlay_reason": _overlay_reason(warnings),
        "worktree_hash": None,
        "snapshot_commit": None,
        "base_commit": None,
        "base_commit_strategy": None,
        "head_commit": None,
        "merge_base": None,
        "reducer_id": reducer_id,
        "projection": projection or None,
        "scope": scope_hint,
        "affected": None,
        "affected_by": list(profile.get("affected_by", [])) if profile else [],
        "warnings": list(warnings),
    }
    payload["_diff"] = diff_payload
    payload["snapshot_warning"] = {
        "code": "DIRTY_NO_OVERLAY",
        "message": (
            "Worktree is dirty but diff overlay is unavailable; reducer output "
            "reflects the last committed snapshot only."
        ),
        "severity": "warning",
    }
    return render_json_payload(payload)


def _resolve_projection(payload: dict[str, object], reducer_id: str | None) -> str:
    projection = str(payload.get("projection", "")).strip().lower()
    if projection:
        return projection
    return str(reducer_id or "").strip().lower()




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


def rows_to_payload(
    worktree_hash: str,
    snapshot_commit: str | None,
    base_commit: str | None,
    base_commit_strategy: str | None,
    head_commit: str | None,
    merge_base: str | None,
    rows: list[dict[str, object]],
    call_rows: list[dict[str, object]],
    summary: dict[str, object] | None,
    warnings: list[str],
) -> OverlayPayload:
    nodes = {"add": [], "remove": [], "modify": []}
    edges = {"add": [], "remove": [], "modify": []}
    for row in rows:
        node_type = row["node_type"]
        diff_kind = row["diff_kind"]
        entry = {
            "structural_id": row["structural_id"],
            "field": row.get("field"),
            "old_value": row.get("old_value"),
            "new_value": row.get("new_value"),
        }
        if node_type == "edge":
            if diff_kind in edges:
                edges[diff_kind].append(entry)
            continue
        if diff_kind in nodes:
            nodes[diff_kind].append(entry)
    calls = {"add": [], "remove": [], "modify": []}
    for row in call_rows:
        diff_kind = row.get("diff_kind")
        entry = dict(row)
        entry.pop("diff_kind", None)
        entry.pop("created_at", None)
        entry.pop("snapshot_id", None)
        if diff_kind in calls:
            calls[diff_kind].append(entry)
    _sort_change_entries(nodes, edges, calls)
    return OverlayPayload(
        worktree_hash=worktree_hash,
        snapshot_commit=snapshot_commit,
        base_commit=base_commit,
        base_commit_strategy=base_commit_strategy,
        head_commit=head_commit,
        merge_base=merge_base,
        nodes=nodes,
        edges=edges,
        calls=calls,
        summary=summary,
        warnings=warnings,
    )


def _parse_entry_payload(entry: dict[str, object]) -> dict[str, object]:
    raw = entry.get("new_value") or entry.get("old_value")
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    if isinstance(value, dict):
        return value
    return {}


def _node_sort_key(entry: dict[str, object]) -> tuple[str, str, str]:
    meta = _parse_entry_payload(entry)
    return (
        str(meta.get("file_path") or ""),
        str(meta.get("qualified_name") or ""),
        str(entry.get("structural_id") or ""),
    )


def _edge_sort_key(entry: dict[str, object]) -> tuple[str, str, str, str, str, str]:
    meta = _parse_entry_payload(entry)
    return (
        str(meta.get("src_file_path") or ""),
        str(meta.get("dst_file_path") or ""),
        str(meta.get("src_qualified_name") or ""),
        str(meta.get("dst_qualified_name") or ""),
        str(meta.get("edge_type") or ""),
        str(entry.get("structural_id") or ""),
    )


def _call_sort_key(entry: dict[str, object]) -> tuple[str, str, str, str, str, str]:
    return (
        str(entry.get("src_file_path") or ""),
        str(entry.get("dst_file_path") or ""),
        str(entry.get("src_qualified_name") or ""),
        str(entry.get("dst_qualified_name") or ""),
        str(entry.get("src_structural_id") or ""),
        str(entry.get("dst_structural_id") or ""),
    )


def _sort_change_entries(
    nodes: dict[str, list[dict[str, object]]],
    edges: dict[str, list[dict[str, object]]],
    calls: dict[str, list[dict[str, object]]],
) -> None:
    for entries in nodes.values():
        entries.sort(key=_node_sort_key)
    for entries in edges.values():
        entries.sort(key=_edge_sort_key)
    for entries in calls.values():
        entries.sort(key=_call_sort_key)


__all__ = [
    "apply_overlay_to_text",
    "get_overlay",
]
