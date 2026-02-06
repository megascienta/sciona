"""Shared exclusion helpers for discovery and overlays."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import pathspec

HARD_EXCLUDES = {".git", ".sciona"}


def is_hard_excluded(rel_path: Path) -> bool:
    return any(part in HARD_EXCLUDES for part in rel_path.parts)


def build_exclude_spec(
    exclude_globs: Sequence[str],
) -> pathspec.PathSpec | None:
    if not exclude_globs:
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", exclude_globs)


def is_excluded_path(
    rel_path: Path,
    *,
    exclude_spec: pathspec.PathSpec | None,
    ignored_paths: Iterable[str] | None = None,
) -> bool:
    if is_hard_excluded(rel_path):
        return True
    posix_path = rel_path.as_posix()
    if ignored_paths and posix_path in ignored_paths:
        return True
    if exclude_spec and exclude_spec.match_file(posix_path):
        return True
    return False

