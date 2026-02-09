# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Read-only storage helpers for addon consumers (stable)."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..data_storage import connections
from ..runtime import paths as runtime_paths


def _resolve_repo_root(repo_root: Path | None) -> Path:
    return repo_root or runtime_paths.get_repo_root()


def open_core_readonly(repo_root: Path | None = None):
    repo_root = _resolve_repo_root(repo_root)
    return connections.connect_core_readonly(runtime_paths.get_db_path(repo_root))


def open_artifact_readonly(repo_root: Path | None = None):
    repo_root = _resolve_repo_root(repo_root)
    return connections.connect_artifact_readonly(
        runtime_paths.get_artifact_db_path(repo_root)
    )


@contextmanager
def core_readonly(repo_root: Path | None = None) -> Iterator[object]:
    repo_root = _resolve_repo_root(repo_root)
    with connections.core_readonly(runtime_paths.get_db_path(repo_root)) as conn:
        yield conn


@contextmanager
def artifact_readonly(repo_root: Path | None = None) -> Iterator[object]:
    repo_root = _resolve_repo_root(repo_root)
    with connections.artifact_readonly(
        runtime_paths.get_artifact_db_path(repo_root)
    ) as conn:
        yield conn


__all__ = [
    "open_core_readonly",
    "open_artifact_readonly",
    "core_readonly",
    "artifact_readonly",
]
