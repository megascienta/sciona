# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer runtime context for DB handles and overlay state owned by pipelines."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

from ....data_storage.artifact_db import connect as artifact_connect
from ....runtime.overlay.types import OverlayPayload

_ARTIFACT_CONN: ContextVar[object | None] = ContextVar(
    "reducer_artifact_conn", default=None
)
_OVERLAY: ContextVar[OverlayPayload | None] = ContextVar(
    "reducer_overlay_payload", default=None
)


def current_artifact_connection() -> object | None:
    return _ARTIFACT_CONN.get()


def fallback_artifact_connection(repo_root: object | None) -> object | None:
    if repo_root is None:
        return None
    root = Path(repo_root)
    artifact_path = root / ".sciona" / "sciona.artifacts.db"
    if not artifact_path.exists():
        return None
    return artifact_connect(artifact_path, repo_root=root)


def current_overlay_payload() -> OverlayPayload | None:
    return _OVERLAY.get()


@contextmanager
def use_artifact_connection(conn: object | None) -> Iterator[None]:
    token = _ARTIFACT_CONN.set(conn)
    try:
        yield
    finally:
        _ARTIFACT_CONN.reset(token)


@contextmanager
def use_overlay_payload(overlay: OverlayPayload | None) -> Iterator[None]:
    token = _OVERLAY.set(overlay)
    try:
        yield
    finally:
        _OVERLAY.reset(token)


__all__ = [
    "current_artifact_connection",
    "current_overlay_payload",
    "fallback_artifact_connection",
    "use_artifact_connection",
    "use_overlay_payload",
]
