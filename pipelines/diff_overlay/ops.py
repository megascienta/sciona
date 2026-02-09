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
from ...runtime.config import defaults as config_defaults
from ...runtime.config import io as config_io
from ...runtime import git as git_ops
from ...runtime import time as runtime_time
from ...runtime.errors import ConfigError, GitError
from ...runtime.logging import get_logger

from .compute import compute_overlay_rows, worktree_fingerprint
from .patch import apply_overlay_to_payload, parse_json_fenced
from .store import overlay_bundle_exists, rows_to_payload
from .types import OverlayPayload

logger = get_logger(__name__)

_LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
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
    repo_root: Path,
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
    diff_scope, scope_exclusions = _resolve_diff_scope(repo_root)
    top_changed = _build_top_changed(overlay, limit=20)
    diff_payload = {
        "version": 2,
        "mode": "full",
        "overlay_available": True,
        "overlay_reason": "available",
        "worktree_hash": overlay.worktree_hash,
        "snapshot_commit": overlay.snapshot_commit,
        "base_commit": overlay.base_commit,
        "head_commit": overlay.head_commit,
        "merge_base": overlay.merge_base,
        "reducer_id": reducer_id,
        "snapshot_id": snapshot_id,
        "projection": projection or None,
        "projection_version": projection_version,
        "changes": {
            "nodes": overlay.nodes,
            "edges": overlay.edges,
            "calls": overlay.calls,
        },
        "summary": overlay.summary,
        "top_changed": top_changed,
        "patched": patched_detail,
        "coverage": _coverage_detail(patched_detail, overlay),
        "warnings": warnings,
        "diff_scope": diff_scope,
        "scope_exclusions": scope_exclusions,
    }
    schema_warnings = _validate_diff_payload(diff_payload)
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
) -> str:
    payload = parse_json_fenced(text)
    if payload is None or "_diff" in payload:
        return text
    projection = str(payload.get("projection", "")).strip().lower()
    diff_scope, scope_exclusions = _resolve_diff_scope(repo_root)
    patched_detail = {
        "projection": False,
        "nodes": False,
        "edges": False,
        "calls": False,
        "summary": False,
        "reasons": ["overlay_unavailable"],
    }
    diff_payload = {
        "version": 2,
        "mode": "full",
        "overlay_available": False,
        "overlay_reason": _overlay_reason(warnings),
        "worktree_hash": None,
        "snapshot_commit": None,
        "base_commit": None,
        "head_commit": None,
        "merge_base": None,
        "reducer_id": reducer_id,
        "snapshot_id": snapshot_id,
        "projection": projection or None,
        "projection_version": payload.get("projection_version"),
        "changes": {
            "nodes": {"add": [], "remove": [], "modify": []},
            "edges": {"add": [], "remove": [], "modify": []},
            "calls": {"add": [], "remove": [], "modify": []},
        },
        "summary": None,
        "top_changed": {"limit": 0, "nodes": [], "edges": [], "calls": []},
        "patched": patched_detail,
        "coverage": {"nodes": "none", "edges": "none", "calls": "none", "summary": "none"},
        "warnings": list(warnings),
        "diff_scope": diff_scope,
        "scope_exclusions": scope_exclusions,
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
    if not isinstance(diff.get("mode"), str):
        warnings.append("schema:mode_not_str")
    if not isinstance(diff.get("overlay_available"), bool):
        warnings.append("schema:overlay_available_not_bool")
    if not isinstance(diff.get("overlay_reason"), str):
        warnings.append("schema:overlay_reason_not_str")
    worktree_hash = diff.get("worktree_hash")
    if worktree_hash is not None and not isinstance(worktree_hash, str):
        warnings.append("schema:worktree_hash_not_str")
    changes = diff.get("changes")
    if not isinstance(changes, dict):
        warnings.append("schema:changes_not_dict")
        changes = {}
    for key in ("nodes", "edges", "calls"):
        value = changes.get(key) if isinstance(changes, dict) else None
        if not isinstance(value, dict):
            warnings.append(f"schema:changes_{key}_not_dict")
            continue
        for diff_kind, entries in value.items():
            if diff_kind not in {"add", "remove", "modify"}:
                warnings.append(f"schema:changes_{key}_invalid_kind:{diff_kind}")
                continue
            if not isinstance(entries, list):
                warnings.append(f"schema:changes_{key}_{diff_kind}_not_list")
    summary = diff.get("summary")
    if summary is not None and not isinstance(summary, dict):
        warnings.append("schema:summary_not_dict")
    top_changed = diff.get("top_changed")
    if not isinstance(top_changed, dict):
        warnings.append("schema:top_changed_not_dict")
    patched = diff.get("patched")
    if not isinstance(patched, dict):
        warnings.append("schema:patched_not_dict")
    coverage = diff.get("coverage")
    if not isinstance(coverage, dict):
        warnings.append("schema:coverage_not_dict")
    diff_scope = diff.get("diff_scope")
    if not isinstance(diff_scope, dict):
        warnings.append("schema:diff_scope_not_dict")
    scope_exclusions = diff.get("scope_exclusions")
    if not isinstance(scope_exclusions, dict):
        warnings.append("schema:scope_exclusions_not_dict")
    return warnings


def _overlay_reason(warnings: list[str]) -> str:
    if "artifact_db_missing" in warnings:
        return "artifact_db_missing"
    if "overlay_unavailable" in warnings:
        return "overlay_unavailable"
    return "overlay_unavailable"


def _resolve_diff_scope(repo_root: Path) -> tuple[dict[str, object], dict[str, object]]:
    try:
        raw = config_io.load_raw_config(repo_root)
    except ConfigError:
        diff_scope = {
            "included_languages": [],
            "tracked_file_types": [],
            "source": "missing_config",
        }
        scope_exclusions = {"discovery_excludes": [], "source": "missing_config"}
        return diff_scope, scope_exclusions

    lang_block = raw.get("languages", {}) if isinstance(raw, dict) else {}
    enabled = []
    for name, defaults in config_defaults.LANGUAGE_DEFAULTS.items():
        user_cfg = lang_block.get(name, {}) if isinstance(lang_block, dict) else {}
        if bool(user_cfg.get("enabled", defaults["enabled"])):
            enabled.append(name)
    enabled = sorted(enabled)

    extensions = []
    for name in enabled:
        extensions.extend(_LANGUAGE_EXTENSIONS.get(name, []))
    extensions = sorted(set(extensions))

    discovery_block = raw.get("discovery", {}) if isinstance(raw, dict) else {}
    exclude_globs = discovery_block.get("exclude_globs", [])
    if not isinstance(exclude_globs, list):
        exclude_globs = []
    cleaned = [str(entry) for entry in exclude_globs if entry]

    diff_scope = {
        "included_languages": enabled,
        "tracked_file_types": extensions,
        "source": "config",
    }
    scope_exclusions = {
        "discovery_excludes": cleaned,
        "source": "config",
    }
    return diff_scope, scope_exclusions


def _parse_overlay_payload(entry: dict[str, object]) -> dict[str, object]:
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


def _build_top_changed(overlay: OverlayPayload, limit: int) -> dict[str, object]:
    return {
        "limit": limit,
        "nodes": _top_nodes(overlay.nodes, limit),
        "edges": _top_edges(overlay.edges, limit),
        "calls": _top_calls(overlay.calls, limit),
    }


def _top_nodes(
    nodes: dict[str, list[dict[str, object]]],
    limit: int,
) -> list[dict[str, object]]:
    order = {
        "module": 0,
        "class": 1,
        "function": 2,
        "method": 3,
        "callable": 4,
    }
    ranked: list[tuple[tuple[int, str, str, str], dict[str, object]]] = []
    for diff_kind in ("add", "modify", "remove"):
        for entry in nodes.get(diff_kind, []):
            meta = _parse_overlay_payload(entry)
            node_type = str(meta.get("node_type") or "")
            qualified_name = str(meta.get("qualified_name") or "")
            file_path = str(meta.get("file_path") or "")
            structural_id = str(entry.get("structural_id") or "")
            rank = order.get(node_type, 99)
            ranked.append(
                (
                    (rank, file_path, qualified_name, structural_id),
                    {
                        "diff_kind": diff_kind,
                        "structural_id": structural_id,
                        "node_type": node_type or None,
                        "qualified_name": qualified_name or None,
                        "file_path": file_path or None,
                    },
                )
            )
    ranked.sort(key=lambda item: item[0])
    return [entry for _, entry in ranked[:limit]]


def _top_edges(
    edges: dict[str, list[dict[str, object]]],
    limit: int,
) -> list[dict[str, object]]:
    ranked: list[tuple[tuple[str, str, str, str, str, str], dict[str, object]]] = []
    for diff_kind in ("add", "modify", "remove"):
        for entry in edges.get(diff_kind, []):
            meta = _parse_overlay_payload(entry)
            structural_id = str(entry.get("structural_id") or "")
            src_file = str(meta.get("src_file_path") or "")
            dst_file = str(meta.get("dst_file_path") or "")
            src_name = str(meta.get("src_qualified_name") or "")
            dst_name = str(meta.get("dst_qualified_name") or "")
            edge_type = str(meta.get("edge_type") or "")
            ranked.append(
                (
                    (src_file, dst_file, src_name, dst_name, edge_type, structural_id),
                    {
                        "diff_kind": diff_kind,
                        "structural_id": structural_id,
                        "edge_type": edge_type or None,
                        "src_structural_id": meta.get("src_structural_id"),
                        "dst_structural_id": meta.get("dst_structural_id"),
                        "src_qualified_name": meta.get("src_qualified_name"),
                        "dst_qualified_name": meta.get("dst_qualified_name"),
                        "src_file_path": meta.get("src_file_path"),
                        "dst_file_path": meta.get("dst_file_path"),
                    },
                )
            )
    ranked.sort(key=lambda item: item[0])
    return [entry for _, entry in ranked[:limit]]


def _top_calls(
    calls: dict[str, list[dict[str, object]]],
    limit: int,
) -> list[dict[str, object]]:
    ranked: list[tuple[tuple[str, str, str, str, str, str], dict[str, object]]] = []
    for diff_kind in ("add", "modify", "remove"):
        for entry in calls.get(diff_kind, []):
            src_file = str(entry.get("src_file_path") or "")
            dst_file = str(entry.get("dst_file_path") or "")
            src_name = str(entry.get("src_qualified_name") or "")
            dst_name = str(entry.get("dst_qualified_name") or "")
            src_id = str(entry.get("src_structural_id") or "")
            dst_id = str(entry.get("dst_structural_id") or "")
            ranked.append(
                (
                    (src_file, dst_file, src_name, dst_name, src_id, dst_id),
                    {
                        "diff_kind": diff_kind,
                        "src_structural_id": entry.get("src_structural_id"),
                        "dst_structural_id": entry.get("dst_structural_id"),
                        "src_node_type": entry.get("src_node_type"),
                        "dst_node_type": entry.get("dst_node_type"),
                        "src_qualified_name": entry.get("src_qualified_name"),
                        "dst_qualified_name": entry.get("dst_qualified_name"),
                        "src_file_path": entry.get("src_file_path"),
                        "dst_file_path": entry.get("dst_file_path"),
                    },
                )
            )
    ranked.sort(key=lambda item: item[0])
    return [entry for _, entry in ranked[:limit]]


__all__ = [
    "apply_overlay_to_text",
    "get_overlay",
]
