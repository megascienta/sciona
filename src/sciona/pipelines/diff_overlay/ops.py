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

_DIFF_MODES = {"full", "summary"}

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
    mode = _normalize_diff_mode(diff_mode)
    payload = parse_json_fenced(text)
    if payload is None:
        if strict:
            raise ValueError("Reducer payload must be JSON.")
        return text
    patched, patched_projection = apply_overlay_to_payload(
        payload, overlay, snapshot_id=snapshot_id, conn=conn, reducer_id=reducer_id
    )
    projection = _resolve_projection(payload, reducer_id)
    projection_version = payload.get("projection_version")
    warnings = list(overlay.warnings)
    if patched_projection is False:
        warnings.append("projection_not_patched")
    if projection in _SUMMARY_PROJECTIONS and overlay.summary is None:
        warnings.append("summary_missing")
    patched_detail = _patched_detail(projection, patched_projection)
    diff_scope, scope_exclusions = _resolve_diff_scope(repo_root)
    scope_hint = _extract_scope_hint(payload, projection)
    scoped_changes, scoped_relevance = _scoped_changes(overlay, scope_hint)
    if mode == "summary":
        changes = _empty_changes()
        top_changed = _empty_top_changed()
    else:
        changes = {
            "nodes": overlay.nodes,
            "edges": overlay.edges,
            "calls": overlay.calls,
        }
        top_changed = _build_top_changed(overlay, limit=20)
    coverage_detail = _coverage_detail_reasons(patched_detail, overlay)
    diff_payload = {
        "version": 2,
        "mode": mode,
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
        "projection_version": projection_version,
        "patch_scope": scope_hint,
        "changes": changes,
        "changes_scoped": scoped_changes,
        "relevance": scoped_relevance,
        "summary": overlay.summary,
        "top_changed": top_changed,
        "patched": patched_detail,
        "coverage": _coverage_detail(patched_detail, overlay),
        "coverage_detail": coverage_detail,
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
    diff_mode: str = "full",
) -> str:
    payload = parse_json_fenced(text)
    if payload is None or "_diff" in payload:
        return text
    mode = _normalize_diff_mode(diff_mode)
    projection = _resolve_projection(payload, reducer_id)
    diff_scope, scope_exclusions = _resolve_diff_scope(repo_root)
    patched_detail = {
        "projection": False,
        "nodes": False,
        "edges": False,
        "calls": False,
        "summary": False,
        "default_partial": False,
        "reasons": ["overlay_unavailable"],
    }
    scope_hint = _extract_scope_hint(payload, projection)
    diff_payload = {
        "version": 2,
        "mode": mode,
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
        "projection_version": payload.get("projection_version"),
        "patch_scope": scope_hint,
        "changes": _empty_changes(),
        "changes_scoped": _empty_changes(),
        "relevance": {
            "affected": False,
            "nodes": {"total": 0, "scoped": 0},
            "edges": {"total": 0, "scoped": 0},
            "calls": {"total": 0, "scoped": 0},
        },
        "summary": None,
        "top_changed": _empty_top_changed(),
        "patched": patched_detail,
        "coverage": {"nodes": "none", "edges": "none", "calls": "none", "summary": "none"},
        "coverage_detail": {
            "nodes": ["overlay_unavailable"],
            "edges": ["overlay_unavailable"],
            "calls": ["overlay_unavailable"],
            "summary": ["overlay_unavailable"],
        },
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


_PROJECTION_COVERAGE: dict[str, dict[str, object]] = {
    "structural_index": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "module_overview": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "callable_overview": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "class_overview": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "file_outline": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "dependency_edges": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "symbol_lookup": {
        "nodes": True,
        "edges": False,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "symbol_references": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": False,
    },
    "callsite_index": {
        "nodes": True,
        "edges": False,
        "calls": True,
        "summary": False,
        "default_partial": True,
    },
    "class_call_graph_summary": {
        "nodes": True,
        "edges": False,
        "calls": True,
        "summary": False,
        "default_partial": True,
    },
    "module_call_graph_summary": {
        "nodes": True,
        "edges": False,
        "calls": True,
        "summary": False,
        "default_partial": True,
    },
    "fan_summary": {
        "nodes": False,
        "edges": True,
        "calls": True,
        "summary": False,
        "default_partial": True,
    },
    "hotspot_summary": {
        "nodes": True,
        "edges": True,
        "calls": False,
        "summary": False,
        "default_partial": True,
    },
}

_SUMMARY_PROJECTIONS = {
    "callsite_index",
    "class_call_graph_summary",
    "module_call_graph_summary",
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
            "default_partial": False,
            "reasons": ["projection_not_supported"],
        }
    coverage = _PROJECTION_COVERAGE.get(
        projection,
        {
            "nodes": False,
            "edges": False,
            "calls": False,
            "summary": False,
            "default_partial": False,
        },
    )
    return {
        "projection": True,
        "nodes": bool(coverage.get("nodes")),
        "edges": bool(coverage.get("edges")),
        "calls": bool(coverage.get("calls")),
        "summary": bool(coverage.get("summary")),
        "default_partial": bool(coverage.get("default_partial")),
        "reasons": [],
    }


def _coverage_detail(
    patched_detail: dict[str, object], overlay: OverlayPayload
) -> dict[str, str]:
    def _coverage(
        flag: bool,
        data: dict[str, list[dict[str, object]]] | None,
        default_partial: bool,
    ) -> str:
        if not flag:
            return "none"
        if not data:
            return "partial" if default_partial else "none"
        if not any(data.values()):
            return "partial" if default_partial else "none"
        return "partial"

    default_partial = bool(patched_detail.get("default_partial"))
    nodes = _coverage(bool(patched_detail.get("nodes")), overlay.nodes, default_partial)
    edges = _coverage(bool(patched_detail.get("edges")), overlay.edges, default_partial)
    calls = _coverage(bool(patched_detail.get("calls")), overlay.calls, default_partial)
    summary = "partial" if patched_detail.get("summary") and overlay.summary else "none"
    return {
        "nodes": nodes,
        "edges": edges,
        "calls": calls,
        "summary": summary,
    }


def _coverage_detail_reasons(
    patched_detail: dict[str, object], overlay: OverlayPayload
) -> dict[str, list[str]]:
    def _reasons(
        flag: bool,
        data: dict[str, list[dict[str, object]]] | None,
        default_partial: bool,
    ) -> list[str]:
        if not flag:
            return ["projection_not_supported"]
        if data is None:
            return ["overlay_missing"]
        if not any(data.values()):
            reasons = ["overlay_empty"]
            if default_partial:
                reasons.append("coverage_default_partial")
            return reasons
        return []

    default_partial = bool(patched_detail.get("default_partial"))
    nodes = _reasons(bool(patched_detail.get("nodes")), overlay.nodes, default_partial)
    edges = _reasons(bool(patched_detail.get("edges")), overlay.edges, default_partial)
    calls = _reasons(bool(patched_detail.get("calls")), overlay.calls, default_partial)
    summary = []
    if not patched_detail.get("summary"):
        summary = ["projection_not_supported"]
    elif overlay.summary is None:
        summary = ["summary_missing"]
    return {
        "nodes": nodes,
        "edges": edges,
        "calls": calls,
        "summary": summary,
    }


def _normalize_diff_mode(diff_mode: str | None) -> str:
    mode = str(diff_mode or "full").strip().lower()
    if mode not in _DIFF_MODES:
        raise ValueError(f"Invalid diff mode '{diff_mode}'.")
    return mode


def _resolve_projection(payload: dict[str, object], reducer_id: str | None) -> str:
    projection = str(payload.get("projection", "")).strip().lower()
    if projection:
        return projection
    return str(reducer_id or "").strip().lower()


def _empty_changes() -> dict[str, dict[str, list[dict[str, object]]]]:
    return {
        "nodes": {"add": [], "remove": [], "modify": []},
        "edges": {"add": [], "remove": [], "modify": []},
        "calls": {"add": [], "remove": [], "modify": []},
    }


def _empty_top_changed() -> dict[str, object]:
    return {"limit": 0, "nodes": [], "edges": [], "calls": []}


def _extract_scope_hint(payload: dict[str, object], projection: str) -> dict[str, object]:
    scope: dict[str, object] = {"scope": "unknown"}
    if projection in {
        "module_overview",
        "dependency_edges",
        "module_call_graph_summary",
    }:
        module_name = payload.get("module_qualified_name") or payload.get("module_filter")
        scope = {
            "scope": "module",
            "module_qualified_name": module_name,
            "module_structural_id": payload.get("module_structural_id")
            or payload.get("module_filter"),
        }
    elif projection in {"callable_overview", "callsite_index"}:
        scope = {
            "scope": "callable",
            "callable_id": payload.get("callable_id") or payload.get("function_id"),
            "qualified_name": payload.get("qualified_name")
            or payload.get("identity", {}).get("qualified_name"),
        }
    elif projection in {"class_overview", "class_call_graph_summary", "class_inheritance"}:
        scope = {
            "scope": "class",
            "class_id": payload.get("class_id"),
            "qualified_name": payload.get("qualified_name"),
        }
    elif projection == "file_outline":
        scope = {
            "scope": "file",
            "file_path": payload.get("file_path"),
            "module_filter": payload.get("module_filter"),
        }
    elif projection == "structural_index":
        scope = {"scope": "codebase"}
    elif projection in {"symbol_lookup", "symbol_references"}:
        scope = {"scope": "query", "query": payload.get("query")}
    elif projection == "fan_summary":
        scope = {
            "scope": "fan",
            "node_id": payload.get("node_id"),
            "module_id": payload.get("module_id"),
            "class_id": payload.get("class_id"),
            "callable_id": payload.get("callable_id") or payload.get("function_id"),
        }
    elif projection == "hotspot_summary":
        scope = {"scope": "codebase"}
    return scope


def _parse_overlay_value(entry: dict[str, object]) -> dict[str, object]:
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


def _scoped_changes(
    overlay: OverlayPayload, scope: dict[str, object]
) -> tuple[dict[str, dict[str, list[dict[str, object]]]], dict[str, object]]:
    if not overlay:
        return _empty_changes(), {
            "affected": False,
            "nodes": {"total": 0, "scoped": 0},
            "edges": {"total": 0, "scoped": 0},
            "calls": {"total": 0, "scoped": 0},
        }
    scope_type = str(scope.get("scope") or "unknown")
    module_name = scope.get("module_qualified_name")
    file_path = scope.get("file_path")
    module_filter = scope.get("module_filter")
    class_id = scope.get("class_id")
    callable_id = scope.get("callable_id")
    node_id = scope.get("node_id")

    def _module_match(name: str | None) -> bool:
        if not name:
            return False
        target = module_name or module_filter
        if not target:
            return False
        return name == target or name.startswith(f"{target}.")

    def _node_match(entry: dict[str, object]) -> bool:
        if scope_type == "codebase":
            return True
        meta = _parse_overlay_value(entry)
        qualified = meta.get("qualified_name")
        if scope_type == "file":
            return bool(file_path and meta.get("file_path") == file_path)
        if scope_type == "module":
            return _module_match(str(qualified)) or _module_match(str(meta.get("module")))
        if scope_type == "callable":
            return str(entry.get("structural_id")) == str(callable_id)
        if scope_type == "class":
            return str(entry.get("structural_id")) == str(class_id)
        if scope_type == "fan":
            return str(entry.get("structural_id")) == str(node_id)
        return False

    def _edge_match(entry: dict[str, object]) -> bool:
        if scope_type == "codebase":
            return True
        meta = _parse_overlay_value(entry)
        src_name = meta.get("src_qualified_name")
        dst_name = meta.get("dst_qualified_name")
        if scope_type == "file":
            return bool(
                file_path
                and (meta.get("src_file_path") == file_path or meta.get("dst_file_path") == file_path)
            )
        if scope_type == "module":
            return _module_match(str(src_name)) or _module_match(str(dst_name))
        if scope_type == "callable":
            return False
        if scope_type == "class":
            return False
        if scope_type == "fan":
            return False
        return False

    def _call_match(entry: dict[str, object]) -> bool:
        if scope_type == "codebase":
            return True
        if scope_type == "callable":
            return str(entry.get("src_structural_id")) == str(callable_id) or str(
                entry.get("dst_structural_id")
            ) == str(callable_id)
        if scope_type == "module":
            src_name = entry.get("src_qualified_name")
            dst_name = entry.get("dst_qualified_name")
            return _module_match(str(src_name)) or _module_match(str(dst_name))
        if scope_type == "file":
            return bool(
                file_path
                and (entry.get("src_file_path") == file_path or entry.get("dst_file_path") == file_path)
            )
        return False

    scoped = _empty_changes()
    total_nodes = 0
    total_edges = 0
    total_calls = 0
    scoped_nodes = 0
    scoped_edges = 0
    scoped_calls = 0

    for kind, entries in overlay.nodes.items():
        total_nodes += len(entries)
        for entry in entries:
            if _node_match(entry):
                scoped["nodes"][kind].append(entry)
                scoped_nodes += 1
    for kind, entries in overlay.edges.items():
        total_edges += len(entries)
        for entry in entries:
            if _edge_match(entry):
                scoped["edges"][kind].append(entry)
                scoped_edges += 1
    for kind, entries in overlay.calls.items():
        total_calls += len(entries)
        for entry in entries:
            if _call_match(entry):
                scoped["calls"][kind].append(entry)
                scoped_calls += 1

    affected: bool | None
    if scope_type == "unknown":
        affected = None
    else:
        affected = any([scoped_nodes > 0, scoped_edges > 0, scoped_calls > 0])
    relevance = {
        "affected": affected,
        "nodes": {"total": total_nodes, "scoped": scoped_nodes},
        "edges": {"total": total_edges, "scoped": scoped_edges},
        "calls": {"total": total_calls, "scoped": scoped_calls},
    }
    return scoped, relevance


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
    patch_scope = diff.get("patch_scope")
    if patch_scope is not None and not isinstance(patch_scope, dict):
        warnings.append("schema:patch_scope_not_dict")
    changes_scoped = diff.get("changes_scoped")
    if changes_scoped is not None and not isinstance(changes_scoped, dict):
        warnings.append("schema:changes_scoped_not_dict")
    relevance = diff.get("relevance")
    if relevance is not None and not isinstance(relevance, dict):
        warnings.append("schema:relevance_not_dict")
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
