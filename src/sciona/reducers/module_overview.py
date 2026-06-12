# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module overview reducer."""

from __future__ import annotations

from .helpers.impl.module_overview import run
from .metadata import ReducerArg, ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="module_overview",
    category="orientation",
    placeholder="MODULE_OVERVIEW",
    summary="Summarizes one module's contained classifiers, callables, and local "
    "structure. Use for first-pass inspection of a module boundary. ",
    args=(
        ReducerArg(
            name="module_id",
            type="str",
            description="Module or package scope to summarize; accepts qualified name or structural id.",
            arg_role="module_scope",
        ),
        ReducerArg(
            name="callable_id",
            type="str",
            description="Resolve the owning module from a callable id.",
        ),
        ReducerArg(
            name="classifier_id",
            type="str",
            description="Resolve the owning module from a classifier id.",
        ),
        ReducerArg(
            name="include_file_map",
            type="bool",
            description="Include the module's file-to-node map.",
            default="false",
        ),
        ReducerArg(
            name="compact",
            type="bool",
            description="Render the compact overview payload.",
            default="false",
        ),
        ReducerArg(
            name="top_k",
            type="int",
            description="Max preview rows in compact mode (capped at 50).",
            default="5",
        ),
    ),
    requires="one of --module-id / --callable-id / --classifier-id",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    include_file_map: bool | None = None,
    compact: bool | None = None,
    top_k: int | str | None = None,
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
        compact=compact,
        top_k=top_k,
    )


__all__ = ["render", "run", "REDUCER_META"]
