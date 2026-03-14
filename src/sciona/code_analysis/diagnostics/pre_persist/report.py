# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Filesystem helpers for optional pre-persist diagnostic runs."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil


def build_status_output_path(repo_root: Path) -> Path:
    return repo_root / f"{repo_root.name}_build_status.json"


def pre_persist_verbose_output_path(repo_root: Path) -> Path:
    return repo_root / f"{repo_root.name}_pre_persist_verbose.json"


@contextmanager
def diagnostic_workspace(sciona_dir: Path):
    workspace = sciona_dir / ".diagnostic_pre_persist"
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
