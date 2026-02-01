"""Tracked-file discovery for ingestion."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Set

import pathspec

from ...runtime import config as core_config
from ..core.normalize.model import FileRecord
from ..core.extract import registry


def collect_files(
    repo_root: Path,
    languages: Dict[str, core_config.LanguageSettings],
    *,
    discovery: Optional[core_config.DiscoverySettings] = None,
    tracked_paths: Optional[Set[str]] = None,
) -> List[FileRecord]:
    if tracked_paths is None:
        raise ValueError("Tracked paths are required for discovery.")
    enabled_languages = [
        name for name, settings in languages.items() if settings.enabled
    ]
    if not enabled_languages:
        return []
    exclude_globs = discovery.exclude_globs if discovery else []
    exclude_spec = (
        pathspec.PathSpec.from_lines("gitwildmatch", exclude_globs)
        if exclude_globs
        else None
    )
    records: List[FileRecord] = []
    for path_str in sorted(tracked_paths):
        rel_path = Path(path_str)
        if _is_explicitly_excluded(rel_path):
            continue
        if exclude_spec and exclude_spec.match_file(rel_path.as_posix()):
            continue
        extension = rel_path.suffix.lower()
        if not extension:
            continue
        language = registry.language_for_extension(extension, enabled_languages)
        if language is None:
            continue
        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue
        records.append(
            FileRecord(
                path=abs_path,
                relative_path=rel_path,
                language=language,
            )
        )
    return records


def _is_explicitly_excluded(rel_path: Path) -> bool:
    parts = rel_path.parts
    if not parts:
        return False
    return parts[0] in {".git", ".sciona"}
