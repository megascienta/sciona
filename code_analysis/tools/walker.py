"""Tracked-file discovery for ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import List, Mapping, Optional, Set

from ...runtime import config as core_config
from . import excludes
from ..core.normalize.model import FileRecord
from ..core.extract import registry


def collect_files(
    repo_root: Path,
    languages: Mapping[str, core_config.LanguageSettings],
    *,
    discovery: Optional[core_config.DiscoverySettings] = None,
    tracked_paths: Optional[Set[str]] = None,
    ignored_paths: Optional[Set[str]] = None,
) -> List[FileRecord]:
    if tracked_paths is None:
        raise ValueError("Tracked paths are required for discovery.")
    enabled_languages = [
        name for name, settings in languages.items() if settings.enabled
    ]
    if not enabled_languages:
        raise ValueError("No enabled languages for discovery.")
    exclude_globs = discovery.exclude_globs if discovery else []
    exclude_spec = excludes.build_exclude_spec(exclude_globs)
    records: List[FileRecord] = []
    for path_str in sorted(tracked_paths):
        rel_path = Path(path_str)
        if excludes.is_excluded_path(
            rel_path,
            exclude_spec=exclude_spec,
            ignored_paths=ignored_paths,
        ):
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
    return excludes.is_hard_excluded(rel_path)
