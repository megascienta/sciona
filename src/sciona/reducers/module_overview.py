# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module overview reducer."""

from __future__ import annotations

from .helpers.impl.module_overview import run
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_overview",
    category="orientation",
    placeholder="MODULE_OVERVIEW",
    summary="Structural summary of a module, including contained classifiers and callables. "
    "Use for architectural inspection. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    include_file_map: bool | None = None,
    **_: object,
) -> str:
    from .helpers.impl.module_overview import render as _render

    return _render(
        snapshot_id,
        conn,
        repo_root,
        module_id=module_id,
        callable_id=callable_id,
        classifier_id=classifier_id,
        include_file_map=include_file_map,
    )


__all__ = ["render", "run", "REDUCER_META"]
