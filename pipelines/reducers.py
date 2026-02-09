# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer registry pipeline helpers."""

from __future__ import annotations

import builtins
from contextlib import nullcontext
from typing import List, Optional, Tuple

from pathlib import Path

from ..reducers.registry import get_reducers, load_reducer
from .resolve import require_identifier
from .policy import repo as policy_repo
from .policy import snapshot as snapshot_policy
from ..data_storage.connections import core
from ..data_storage.connections import artifact as artifact_db
from . import diff_overlay
from .errors import WorkflowError
from ..runtime.paths import get_artifact_db_path, get_db_path
from ..reducers.helpers.context import use_artifact_connection


def _ensure_clean_repo(repo_root: Optional[Path] = None) -> None:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)


def list_entries(
    repo_root: Optional[Path] = None,
    *,
    include_hidden: bool = False,
) -> List[dict[str, object]]:
    _ensure_clean_repo(repo_root)
    reducers = get_reducers()
    entries = []
    for reducer_id, entry in reducers.items():
        entries.append(
            {
                "reducer_id": reducer_id,
                "scope": entry.scope,
                "placeholders": builtins.list(entry.placeholders),
                "determinism": entry.determinism,
                "payload_size_stats": entry.payload_size_stats,
                "semantic_tag": entry.semantic_tag,
                "summary": entry.summary,
                "lossy": entry.lossy,
                "baseline_only": entry.baseline_only,
                "composite": entry.composite,
            }
        )
    return sorted(entries, key=lambda item: item["reducer_id"])


def get_entry(
    reducer_id: str,
    repo_root: Optional[Path] = None,
    *,
    include_hidden: bool = False,
) -> dict[str, object]:
    entries = list_entries(repo_root, include_hidden=include_hidden)
    for entry in entries:
        if entry["reducer_id"] == reducer_id:
            return entry
    raise ValueError(f"Unknown reducer '{reducer_id}'.")


def emit(
    reducer_id: str,
    *,
    repo_root: Optional[Path] = None,
    **kwargs: object,
) -> Tuple[str, str, dict[str, object]]:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)
    db_path = get_db_path(repo_state.repo_root)
    if not db_path.exists():
        raise WorkflowError(
            "No committed snapshots available. Run 'sciona build' first.",
            code="missing_snapshot",
        )
    try:
        reducer = load_reducer(reducer_id)
    except ValueError as exc:
        raise WorkflowError(str(exc), code="unknown_reducer") from exc
    if not hasattr(reducer, "render"):
        raise WorkflowError(
            f"Reducer '{reducer_id}' cannot be rendered.", code="invalid_reducer"
        )
    with core(db_path, repo_root=repo_state.repo_root) as conn:
        snapshot_id = snapshot_policy.resolve_latest_snapshot(conn)
        resolved_kwargs = _resolve_reducer_identifiers(conn, snapshot_id, kwargs)
        artifact_path = get_artifact_db_path(repo_state.repo_root)
        artifact_scope = (
            artifact_db(artifact_path, repo_root=repo_state.repo_root)
            if artifact_path.exists()
            else nullcontext(None)
        )
        try:
            is_dirty = repo_state.git.is_worktree_dirty(repo_state.repo_root)
        except Exception:
            is_dirty = False
        with artifact_scope as artifact_conn:
            with use_artifact_connection(artifact_conn):
                overlay = diff_overlay.get_overlay(
                    repo_root=repo_state.repo_root,
                    snapshot_id=snapshot_id,
                    core_conn=conn,
                    artifact_conn=artifact_conn,
                )
                try:
                    text = reducer.render(
                        snapshot_id, conn, repo_state.repo_root, **resolved_kwargs
                    )
                except ValueError as exc:
                    raise WorkflowError(str(exc), code="reducer_error") from exc
                try:
                    text = diff_overlay.apply_overlay_to_text(
                        text,
                        overlay,
                        snapshot_id=snapshot_id,
                        conn=conn,
                        strict=True,
                        reducer_id=reducer_id,
                    )
                except ValueError as exc:
                    raise WorkflowError(
                        f"Reducer '{reducer_id}' must return JSON.", code="invalid_json"
                    ) from exc
                if is_dirty and overlay is None:
                    warnings = ["dirty_worktree", "overlay_unavailable"]
                    if artifact_conn is None:
                        warnings.append("artifact_db_missing")
                    text = diff_overlay.attach_unavailable_overlay(
                        text,
                        snapshot_id=snapshot_id,
                        reducer_id=reducer_id,
                        warnings=warnings,
                    )
    return text, snapshot_id, resolved_kwargs


def _resolve_reducer_identifiers(
    conn,
    snapshot_id: str,
    kwargs: dict[str, object],
) -> dict[str, object]:
    resolved = dict(kwargs)
    callable_id = resolved.pop("callable_id", None)
    if callable_id and (resolved.get("function_id") or resolved.get("method_id")):
        raise WorkflowError(
            "Provide only one of callable_id, function_id, or method_id.",
            code="invalid_parameters",
        )

    resolved_callable = False
    if callable_id:
        resolved["function_id"] = require_identifier(
            conn,
            snapshot_id,
            kind="callable",
            identifier=callable_id,
        )
        resolved_callable = True

    id_kinds = {
        "function_id": "function",
        "method_id": "method",
        "class_id": "class",
        "module_id": "module",
        "from_module_id": "module",
        "to_module_id": "module",
    }
    for key, kind in id_kinds.items():
        value = resolved.get(key)
        if not value or not isinstance(value, str):
            continue
        if resolved_callable and key == "function_id":
            continue
        resolved[key] = require_identifier(
            conn,
            snapshot_id,
            kind=kind,
            identifier=value,
        )
    return resolved
