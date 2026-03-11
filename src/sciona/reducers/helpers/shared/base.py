# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared reducer helpers."""

from __future__ import annotations

from ... import (
    callable_overview,
    classifier_overview,
    module_overview,
    structural_index,
)
from . import queries
from .connection import require_connection
from .types import (
    CallableOverviewPayload,
    ClassifierOverviewPayload,
    ModuleOverviewPayload,
    StructuralIndexPayload,
)


# Reducers must emit a single top-level Markdown block (e.g., one fenced code block).
def resolve_callable_id(conn, snapshot_id: str, callable_id: str | None) -> str:
    conn = require_connection(conn)
    return queries.resolve_callable_id(conn, snapshot_id, callable_id)


def resolve_classifier_id(conn, snapshot_id: str, classifier_id: str | None) -> str:
    conn = require_connection(conn)
    return queries.resolve_classifier_id(conn, snapshot_id, classifier_id)


def load_callable_overview(
    snapshot_id: str,
    conn,
    repo_root,
    callable_id: str | None,
) -> CallableOverviewPayload:
    conn = require_connection(conn)
    resolved_id = resolve_callable_id(conn, snapshot_id, callable_id)
    return callable_overview.run(
        snapshot_id,
        conn=conn,
        callable_id=resolved_id,
        repo_root=repo_root,
    )


def load_classifier_overview(
    snapshot_id: str,
    conn,
    repo_root,
    classifier_id: str | None,
) -> ClassifierOverviewPayload:
    conn = require_connection(conn)
    resolved_id = resolve_classifier_id(conn, snapshot_id, classifier_id)
    return classifier_overview.run(
        snapshot_id,
        conn=conn,
        classifier_id=resolved_id,
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
