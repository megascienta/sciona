# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diff overlay schema validation helpers."""

from __future__ import annotations


def validate_diff_payload(diff: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    if not isinstance(diff.get("version"), int):
        warnings.append("schema:version_not_int")
    if not isinstance(diff.get("overlay_available"), bool):
        warnings.append("schema:overlay_available_not_bool")
    if not isinstance(diff.get("overlay_reason"), str):
        warnings.append("schema:overlay_reason_not_str")
    worktree_hash = diff.get("worktree_hash")
    if worktree_hash is not None and not isinstance(worktree_hash, str):
        warnings.append("schema:worktree_hash_not_str")
    scope = diff.get("scope")
    if scope is not None and not isinstance(scope, dict):
        warnings.append("schema:scope_not_dict")
    affected_by = diff.get("affected_by")
    if affected_by is not None and not isinstance(affected_by, list):
        warnings.append("schema:affected_by_not_list")
    affected = diff.get("affected")
    if affected is not None and not isinstance(affected, bool):
        warnings.append("schema:affected_not_bool")
    return warnings


__all__ = ["validate_diff_payload"]
