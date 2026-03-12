# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared language-scope helpers for enabled-language file coverage."""

from __future__ import annotations

from typing import Iterable, Mapping, Set

from ...code_analysis.core.extract.registry import extensions_for_language
from .defaults import LANGUAGE_DEFAULTS
from .models import LanguageSettings


def all_tracked_extensions() -> Set[str]:
    extensions: Set[str] = set()
    for name in LANGUAGE_DEFAULTS:
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions


def enabled_tracked_extensions(
    languages: Mapping[str, LanguageSettings],
) -> Set[str]:
    extensions: Set[str] = set()
    for name, lang_settings in languages.items():
        if not lang_settings.enabled:
            continue
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions


def tracked_extensions_for_enabled_names(enabled_languages: Iterable[str]) -> Set[str]:
    extensions: Set[str] = set()
    for name in enabled_languages:
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions


__all__ = [
    "all_tracked_extensions",
    "enabled_tracked_extensions",
    "tracked_extensions_for_enabled_names",
]
