# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared helpers for language extractors."""

from __future__ import annotations

from pathlib import Path

from ...normalize.model import FileSnapshot


def repo_root_from_snapshot(snapshot: FileSnapshot) -> Path:
    rel_parts = snapshot.record.relative_path.parts
    if not rel_parts:
        return snapshot.record.path.parent
    return snapshot.record.path.parents[len(rel_parts) - 1]


def is_internal_module(module_name: str, module_index: set[str] | None) -> bool:
    if module_index is None:
        return False
    return module_name in module_index

