"""Routing helpers for ingest orchestration."""
from __future__ import annotations

from typing import Dict, Optional

from .extract import registry
from .normalize.model import FileSnapshot
from ...runtime import config as core_config


AnalyzerMap = Dict[str, object]


def select_analyzers(languages: Dict[str, core_config.LanguageSettings]) -> AnalyzerMap:
    """Return analyzers for enabled languages only."""
    analyzers: AnalyzerMap = {}
    for language, settings in languages.items():
        if not settings.enabled:
            continue
        analyzer = registry.get_analyzer(language)
        if analyzer:
            analyzers[language] = analyzer
    return analyzers


def resolve_analyzer(file_snapshot: FileSnapshot, analyzers: AnalyzerMap) -> Optional[object]:
    """Pick the analyzer for a file snapshot, if any."""
    return registry.get_analyzer_for_path(file_snapshot.record.path, analyzers)


def should_register_module(file_snapshot: FileSnapshot, analyzer: Optional[object]) -> bool:
    """Routing gate for module registration during ingest."""
    return analyzer is not None
