# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer helpers."""

from __future__ import annotations

from ..structural import (
    callable_overview,
    class_overview,
    module_overview,
    structural_index,
)
from . import queries
from .render import require_connection
from .types import (
    CallableOverviewPayload,
    ClassOverviewPayload,
    ModuleOverviewPayload,
    StructuralIndexPayload,
)


# Reducers must emit a single top-level Markdown block (e.g., one fenced code block).
def resolve_function_id(conn, snapshot_id: str, function_id: str | None) -> str:
    conn = require_connection(conn)
    return queries.resolve_function_id(conn, snapshot_id, function_id)


def resolve_method_id(conn, snapshot_id: str, method_id: str | None) -> str:
    conn = require_connection(conn)
    return queries.resolve_method_id(conn, snapshot_id, method_id)


def resolve_class_id(conn, snapshot_id: str, class_id: str | None) -> str:
    conn = require_connection(conn)
    return queries.resolve_class_id(conn, snapshot_id, class_id)


def load_function_overview(
    snapshot_id: str,
    conn,
    repo_root,
    function_id: str | None,
) -> CallableOverviewPayload:
    conn = require_connection(conn)
    resolved_id = resolve_function_id(conn, snapshot_id, function_id)
    return callable_overview.run(
        snapshot_id,
        conn=conn,
        function_id=resolved_id,
        repo_root=repo_root,
    )


def load_method_overview(
    snapshot_id: str,
    conn,
    repo_root,
    method_id: str | None,
) -> CallableOverviewPayload:
    conn = require_connection(conn)
    resolved_id = resolve_method_id(conn, snapshot_id, method_id)
    return callable_overview.run(
        snapshot_id,
        conn=conn,
        function_id=resolved_id,
        repo_root=repo_root,
    )


def load_callable_overview(
    snapshot_id: str,
    conn,
    repo_root,
    function_id: str | None = None,
    method_id: str | None = None,
) -> CallableOverviewPayload:
    conn = require_connection(conn)
    if method_id:
        resolved_id = resolve_method_id(conn, snapshot_id, method_id)
    else:
        resolved_id = resolve_function_id(conn, snapshot_id, function_id)
    return callable_overview.run(
        snapshot_id,
        conn=conn,
        function_id=resolved_id,
        repo_root=repo_root,
    )


def load_class_overview(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None,
) -> ClassOverviewPayload:
    conn = require_connection(conn)
    resolved_id = resolve_class_id(conn, snapshot_id, class_id)
    return class_overview.run(
        snapshot_id,
        conn=conn,
        class_id=resolved_id,
        repo_root=repo_root,
    )


def load_structural_index(snapshot_id: str, conn, repo_root) -> StructuralIndexPayload:
    conn = require_connection(conn)
    return structural_index.run(
        snapshot_id,
        conn=conn,
        repo_root=repo_root,
    )


def load_module_overview(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str,
) -> ModuleOverviewPayload:
    conn = require_connection(conn)
    return module_overview.run(
        snapshot_id,
        conn=conn,
        module_id=module_id,
        repo_root=repo_root,
    )
