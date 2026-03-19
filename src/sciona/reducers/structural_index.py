# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Canonical structural_index reducer."""

from __future__ import annotations

from .helpers.impl.structural_index import run
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="structural_index",
    category="orientation",
    placeholder="STRUCTURAL_INDEX",
    summary="Provides the repo-wide structural inventory across modules, classifiers, "
    "and callables. Use for top-level codebase orientation or structural validation. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    compact: bool | None = None,
    top_k: int | str | None = None,
    **_: object,
) -> str:
    from .helpers.impl.structural_index import render as _render

    return _render(snapshot_id, conn, repo_root, compact=compact, top_k=top_k)


__all__ = ["render", "run", "REDUCER_META"]
