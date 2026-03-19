# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol reference reducer."""

from __future__ import annotations

from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="symbol_references",
    category="symbol",
    placeholder="SYMBOL_REFERENCES",
    summary="Shows where matching structural symbols appear across modules and files. "
    "Use when tracking symbol presence and spread rather than resolving one best match. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    query: str | None = None,
    kind: str | None = None,
    module_id: str | None = None,
    limit: int | str | None = 20,
    **_: object,
) -> str:
    from .helpers.impl.symbol_references import render as _render

    return _render(
        snapshot_id,
        conn,
        repo_root,
        query=query,
        kind=kind,
        module_id=module_id,
        limit=limit,
    )


__all__ = ["render", "REDUCER_META"]
