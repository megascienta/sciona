# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Discovery helpers shared across CLI and pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence, Set

import pathspec

from ...core.extract import registry
from ...core.normalize.model import FileRecord
from . import excludes


def compute_discovery_details(
    tracked_paths: Iterable[str],
    enabled_languages: Sequence[str],
    records: Sequence[FileRecord],
    exclude_globs: Sequence[str],
    ignored_paths: Set[str] | None = None,
) -> tuple[dict[str, int], dict[str, int], dict[str, int], int]:
    candidate_counts = {language: 0 for language in enabled_languages}
    candidate_paths: list[str] = []
    for path_str in tracked_paths:
        rel_path = Path(path_str)
        if excludes.is_hard_excluded(rel_path):
            continue
        posix_path = rel_path.as_posix()
        if ignored_paths and posix_path in ignored_paths:
            continue
        extension = rel_path.suffix.lower()
        if not extension:
            continue
        language = registry.language_for_extension(extension, enabled_languages)
        if not language:
            continue
        candidate_counts[language] += 1
        candidate_paths.append(posix_path)

    discovered_counts = {language: 0 for language in enabled_languages}
    for record in records:
        if record.language in discovered_counts:
            discovered_counts[record.language] += 1

    excluded_by_glob: dict[str, int] = {}
    excluded_set: set[str] = set()
    if exclude_globs:
        specs = [
            (pattern, pathspec.PathSpec.from_lines("gitwildmatch", [pattern]))
            for pattern in exclude_globs
        ]
        for pattern, _spec in specs:
            excluded_by_glob[pattern] = 0
        for path_str in candidate_paths:
            matched = False
            for pattern, spec in specs:
                if spec.match_file(path_str):
                    excluded_by_glob[pattern] += 1
                    matched = True
            if matched:
                excluded_set.add(path_str)
    excluded_total = len(excluded_set)
    return candidate_counts, discovered_counts, excluded_by_glob, excluded_total


def detect_languages_from_tracked_paths(
    tracked_paths: Iterable[str],
    available_languages: Sequence[str],
    ignored_paths: Set[str] | None = None,
) -> list[str]:
    """Infer languages present in tracked paths based on known extensions."""
    detected: set[str] = set()
    for path_str in tracked_paths:
        rel_path = Path(path_str)
        if excludes.is_hard_excluded(rel_path):
            continue
        posix_path = rel_path.as_posix()
        if ignored_paths and posix_path in ignored_paths:
            continue
        extension = rel_path.suffix.lower()
        if not extension:
            continue
        language = registry.language_for_extension(extension, available_languages)
        if language:
            detected.add(language)
    return sorted(detected)
