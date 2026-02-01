"""Language registry for ingestion analyzers and extensions."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple

from ...config import LANGUAGE_CONFIG
from .analyzer import ASTAnalyzer
AnalyzerFactory = Callable[[], ASTAnalyzer]


def get_analyzer(language: str) -> Optional[ASTAnalyzer]:
    config = LANGUAGE_CONFIG.get(language)
    if not config or not config.analyzer_factory:
        return None
    return config.analyzer_factory()


def extensions_for_language(language: str) -> Tuple[str, ...]:
    config = LANGUAGE_CONFIG.get(language)
    if not config:
        return ()
    return config.extensions


def language_for_extension(extension: str, enabled_languages: Iterable[str]) -> Optional[str]:
    normalized = extension.lower()
    for language in enabled_languages:
        if normalized in extensions_for_language(language):
            return language
    return None


def get_analyzer_for_path(
    path: Path,
    analyzers: Dict[str, ASTAnalyzer],
) -> Optional[ASTAnalyzer]:
    extension = path.suffix.lower()
    language = _language_for_extension(extension)
    if not language:
        return None
    return analyzers.get(language)


def _language_for_extension(extension: str) -> Optional[str]:
    for language, config in LANGUAGE_CONFIG.items():
        if extension in config.extensions:
            return language
    return None
