# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Descriptor-first language registry for extraction wiring."""

from __future__ import annotations

from ...config import LANGUAGE_CONFIG
from .language_adapter import LanguageDescriptor


def descriptors() -> dict[str, LanguageDescriptor]:
    """Return static language descriptors keyed by language id."""
    registered: dict[str, LanguageDescriptor] = {}
    for language_id, config in LANGUAGE_CONFIG.items():
        registered[language_id] = LanguageDescriptor(
            language_id=language_id,
            extensions=config.extensions,
            callable_types=config.callable_types,
            analyzer_factory=config.analyzer_factory,
            module_namer=config.module_namer,
        )
    return registered


def get_descriptor(language_id: str) -> LanguageDescriptor | None:
    return descriptors().get(language_id)


def supported_languages() -> tuple[str, ...]:
    return tuple(sorted(descriptors().keys()))


__all__ = ["descriptors", "get_descriptor", "supported_languages"]
