# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer registry pipeline helpers."""

from __future__ import annotations

import builtins
import inspect
from contextlib import nullcontext
from typing import List, Optional, Tuple

from pathlib import Path

from ...reducers.registry import get_reducers, load_reducer
from .resolve import require_identifier
from ..policy import repo as policy_repo
from ..policy import snapshot as snapshot_policy
from ...data_storage.connections import core
from ...data_storage.connections import artifact as artifact_db
from .. import diff_overlay
from ..errors import WorkflowError
from ...runtime.paths import get_artifact_db_path, get_db_path
from ...reducers.helpers.shared.context import (
    use_artifact_connection,
    use_overlay_payload,
)


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
                "category": entry.category,
                "placeholder": entry.placeholder,
                "risk_tier": entry.risk_tier,
                "stage": entry.stage,
                "summary": entry.summary,
                "anomaly_detector": entry.anomaly_detector,
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
    diff_mode: str = "full",
    **kwargs: object,
) -> Tuple[dict[str, object], str, dict[str, object]]:
    repo_state = policy_repo.resolve_repo_state(repo_root, allow_missing_config=True)
    policy_repo.ensure_initialized(repo_state)
    normalized_diff_mode = str(diff_mode or "full").strip().lower()
    if normalized_diff_mode not in {"full", "summary"}:
        raise WorkflowError(
            f"Invalid diff mode '{diff_mode}'.",
            code="invalid_diff_mode",
        )
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
    _validate_reducer_kwargs(reducer, kwargs)
    with core(db_path, repo_root=repo_state.repo_root) as conn:
        snapshot_id = snapshot_policy.resolve_latest_snapshot(conn)
        resolved_kwargs = _resolve_reducer_identifiers(conn, snapshot_id, kwargs)
        resolved_kwargs["diff_mode"] = normalized_diff_mode
        artifact_path = get_artifact_db_path(repo_state.repo_root)
        artifact_scope = (
            artifact_db(artifact_path, repo_root=repo_state.repo_root)
            if artifact_path.exists()
            else nullcontext(None)
        )
        try:
            scoped_dirty = bool(policy_repo.dirty_worktree_warning(repo_state))
        except Exception:
            scoped_dirty = False
        with artifact_scope as artifact_conn:
            with use_artifact_connection(artifact_conn):
                overlay = None
                if scoped_dirty:
                    overlay = diff_overlay.get_overlay(
                        repo_root=repo_state.repo_root,
                        snapshot_id=snapshot_id,
                        core_conn=conn,
                        artifact_conn=artifact_conn,
                    )
                try:
                    render_kwargs = dict(resolved_kwargs)
                    render_kwargs.pop("diff_mode", None)
                    with use_overlay_payload(overlay):
                        payload = reducer.render(
                            snapshot_id, conn, repo_state.repo_root, **render_kwargs
                        )
                except ValueError as exc:
                    raise WorkflowError(str(exc), code="reducer_error") from exc
                if not isinstance(payload, dict):
                    raise WorkflowError(
                        f"Reducer '{reducer_id}' must return a JSON object.",
                        code="invalid_json",
                    )
                try:
                    payload = diff_overlay.apply_overlay_to_payload_object(
                        payload,
                        overlay,
                        repo_root=repo_state.repo_root,
                        snapshot_id=snapshot_id,
                        conn=conn,
                        strict=True,
                        reducer_id=reducer_id,
                        diff_mode=normalized_diff_mode,
                    )
                except ValueError as exc:
                    raise WorkflowError(
                        f"Reducer '{reducer_id}' must return JSON.",
                        code="invalid_json",
                    ) from exc
                if scoped_dirty and overlay is None:
                    warnings = ["dirty_worktree", "overlay_unavailable"]
                    if artifact_conn is None:
                        warnings.append("artifact_db_missing")
                    payload = diff_overlay.attach_unavailable_overlay(
                        payload,
                        repo_root=repo_state.repo_root,
                        snapshot_id=snapshot_id,
                        reducer_id=reducer_id,
                        warnings=warnings,
                        diff_mode=normalized_diff_mode,
                    )
    return payload, snapshot_id, resolved_kwargs


def _resolve_reducer_identifiers(
    conn,
    snapshot_id: str,
    kwargs: dict[str, object],
) -> dict[str, object]:
    resolved = dict(kwargs)
    callable_id = resolved.get("callable_id")

    if callable_id:
        resolved["callable_id"] = require_identifier(
            conn,
            snapshot_id,
            kind="callable",
            identifier=callable_id,
        )

    id_kinds = {
        "classifier_id": "classifier",
        "module_id": "module",
        "from_module_id": "module",
        "to_module_id": "module",
    }
    for key, kind in id_kinds.items():
        value = resolved.get(key)
        if not value or not isinstance(value, str):
            continue
        resolved[key] = require_identifier(
            conn,
            snapshot_id,
            kind=kind,
            identifier=value,
        )
    return resolved


def _validate_reducer_kwargs(reducer, kwargs: dict[str, object]) -> None:
    render = getattr(reducer, "render", None)
    if render is None:
        return
    reserved = {"snapshot_id", "conn", "repo_root"}
    allowed = {
        name
        for name, param in inspect.signature(render).parameters.items()
        if name not in reserved and param.kind is not inspect.Parameter.VAR_KEYWORD
    }
    unknown = sorted(name for name in kwargs.keys() if name not in allowed)
    if unknown:
        names = ", ".join(repr(name) for name in unknown)
        raise WorkflowError(
            f"Unknown reducer parameter(s): {names}.",
            code="invalid_parameters",
        )
