# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dirty-worktree diff overlay helpers for reducer payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .affection import extract_scope_hint, scoped_affection
from .ops_get import _OVERLAY_PROFILE, _overlay_reason
from .patch import apply_overlay_to_payload
from .schema import validate_diff_payload
from .types import OverlayPayload

def apply_overlay_to_payload_object(
    payload: dict[str, object],
    overlay: Optional[OverlayPayload],
    *,
    repo_root: Path,
    snapshot_id: str,
    conn,
    strict: bool = False,
    reducer_id: str | None = None,
    diff_mode: str = "full",
) -> dict[str, object]:
    if not overlay:
        return payload
    reducer_applied_overlay = bool(payload.pop("_overlay_applied_by_reducer", False))
    if reducer_applied_overlay:
        patched = payload
        patched_projection = True
    else:
        patched, patched_projection = apply_overlay_to_payload(
            payload, overlay, snapshot_id=snapshot_id, conn=conn, reducer_id=reducer_id
        )
    projection = _resolve_projection(payload, reducer_id)
    warnings = list(overlay.warnings)
    profile = _OVERLAY_PROFILE.get(projection, None)
    scope_hint = extract_scope_hint(payload, profile)
    affected, affected_by = scoped_affection(overlay, scope_hint, profile)
    if profile and not profile.get("supports_patch"):
        warnings.append("projection_not_supported")
        affected = None
    elif not patched_projection:
        warnings.append("projection_not_patched")
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
    if profile and not profile.get("supports_patch"):
        patched["snapshot_warning"] = {
            "code": "DIRTY_OVERLAY_METADATA_ONLY",
            "message": (
                "Worktree is dirty and overlay metadata is available, but this "
                "projection is not payload-patchable; reducer output remains "
                "committed-snapshot only."
            ),
            "severity": "warning",
        }
    return patched

def attach_unavailable_overlay(
    payload: dict[str, object],
    *,
    repo_root: Path,
    snapshot_id: str,
    reducer_id: str | None,
    warnings: list[str],
    diff_mode: str = "full",
) -> dict[str, object]:
    if "_diff" in payload:
        return payload
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
    return payload

def _resolve_projection(payload: dict[str, object], reducer_id: str | None) -> str:
    projection = str(payload.get("projection", "")).strip().lower()
    if projection:
        return projection
    return str(reducer_id or "").strip().lower()
