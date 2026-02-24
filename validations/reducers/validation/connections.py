# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

from sciona.api import addons as sciona_api


def open_core_db(repo_root: Path):
    return sciona_api.core_readonly(repo_root)


def open_artifact_db(repo_root: Path):
    return sciona_api.artifact_readonly(repo_root)
