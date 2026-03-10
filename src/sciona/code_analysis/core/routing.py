# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Routing helpers for ingest orchestration."""

from __future__ import annotations

from typing import Dict, Optional

from .extract import registry
from .extract.interfaces import language_registry
from .normalize.model import FileSnapshot
from ...runtime import config as core_config
from ...runtime.errors import IngestionError


AnalyzerMap = Dict[str, object]


def select_analyzers(languages: Dict[str, core_config.LanguageSettings]) -> AnalyzerMap:
    """Return analyzers for enabled languages only."""
    analyzers: AnalyzerMap = {}
    missing: list[str] = []
    for language, settings in languages.items():
        if not settings.enabled:
            continue
        descriptor = language_registry.get_descriptor(language)
        if descriptor is not None:
            try:
                language_registry.assert_descriptor_compliant(language)
            except ValueError as exc:
                raise IngestionError(str(exc)) from exc
        analyzer = registry.get_analyzer(language)
        if analyzer:
            analyzers[language] = analyzer
            continue
        hint = language_registry.install_hint_for(language)
        if hint:
            missing.append(f"{language} (install with: {hint})")
        else:
            missing.append(language)
    if missing:
        joined = ", ".join(sorted(missing))
        raise IngestionError(f"Enabled language adapters are unavailable: {joined}")
    return analyzers


def resolve_analyzer(
    file_snapshot: FileSnapshot, analyzers: AnalyzerMap
) -> Optional[object]:
    """Pick the analyzer for a file snapshot, if any."""
    return registry.get_analyzer_for_path(file_snapshot.record.path, analyzers)


def should_register_module(
    file_snapshot: FileSnapshot, analyzer: Optional[object]
) -> bool:
    """Routing gate for module registration during ingest."""
    return analyzer is not None
