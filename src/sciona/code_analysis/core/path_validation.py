# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Path-containment checks shared by ingestion and workspace snapshot helpers."""

from __future__ import annotations

from pathlib import Path


def expected_repo_root(path: Path, relative_path: Path) -> Path:
    depth = len(relative_path.parts) - 1
    return path.parents[depth] if depth >= 0 else path.parent


def validate_record_path_containment(path: Path, relative_path: Path) -> None:
    repo_root = expected_repo_root(path, relative_path)
    expected_path = repo_root / relative_path
    if path != expected_path:
        raise ValueError("FileRecord path does not match derived repo-relative path.")
    ensure_repo_contained(repo_root, path)


def ensure_repo_contained(repo_root: Path, path: Path) -> None:
    resolved_repo = repo_root.resolve()
    resolved_path = path.resolve()
    resolved_path.relative_to(resolved_repo)
