# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Callsite index reducer."""

from __future__ import annotations

from .helpers.impl.callsite_index import build_neighbors_payload
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="callsite_index",
    category="symbol",
    placeholder="CALLSITE_INDEX",
    summary="Lists persisted callsite resolution results for one callable, with optional "
    "filters for identifier, status, provenance, and drop reason. "
    "detail_level='neighbors' returns caller/callee sets. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None = None,
    direction: str | None = None,
    detail_level: str | None = None,
    include_callsite_diagnostics: bool | None = None,
    identifier: str | None = None,
    status: str | None = None,
    provenance: str | None = None,
    drop_reason: str | None = None,
    compact: bool | None = None,
    **_: object,
) -> str:
    from .helpers.impl.callsite_index import render as _render

    return _render(
        snapshot_id,
        conn,
        repo_root,
        callable_id=callable_id,
        direction=direction,
        detail_level=detail_level,
        include_callsite_diagnostics=include_callsite_diagnostics,
        identifier=identifier,
        status=status,
        provenance=provenance,
        drop_reason=drop_reason,
        compact=compact,
    )


__all__ = ["render", "build_neighbors_payload", "REDUCER_META"]
