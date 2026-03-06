# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Canonical structural_index reducer."""

from __future__ import annotations

from .helpers.structural_index_impl import run
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="structural_index",
    category="structure",
    risk_tier="normal",
    stage="initial_scan",
    placeholder="STRUCTURAL_INDEX",
    summary="Canonical structural index of the codebase. "
    "Use for global structural reasoning or validation. ",
)


def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    from .helpers.structural_index_impl import render as _render

    return _render(snapshot_id, conn, repo_root)


__all__ = ["render", "run", "REDUCER_META"]
