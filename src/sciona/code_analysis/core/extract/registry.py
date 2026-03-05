# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language registry for ingestion analyzers and extensions."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Tuple

from .analyzer import ASTAnalyzer
from .language_registry import get_descriptor

AnalyzerFactory = Callable[[], ASTAnalyzer]


def get_analyzer(language: str) -> Optional[ASTAnalyzer]:
    descriptor = get_descriptor(language)
    if not descriptor or not descriptor.extractor_factory:
        return None
    return descriptor.extractor_factory()


def extensions_for_language(language: str) -> Tuple[str, ...]:
    descriptor = get_descriptor(language)
    if not descriptor:
        return ()
    return descriptor.extensions


def language_for_extension(
    extension: str, enabled_languages: Iterable[str]
) -> Optional[str]:
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
    language = language_for_extension(extension, analyzers.keys())
    if not language:
        return None
    return analyzers.get(language)
