# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Neutral access helpers for dirty-worktree overlay data."""

from __future__ import annotations


def load_overlay(
    *,
    repo_root,
    snapshot_id: str,
    core_conn,
    artifact_conn,
):
    from .pipelines.diff_overlay.ops_get import get_overlay

    return get_overlay(
        repo_root=repo_root,
        snapshot_id=snapshot_id,
        core_conn=core_conn,
        artifact_conn=artifact_conn,
    )


__all__ = ["load_overlay"]
