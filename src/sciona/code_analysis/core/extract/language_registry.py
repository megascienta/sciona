# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Descriptor-first language registry for extraction wiring."""

from __future__ import annotations

from ...config import LANGUAGE_CONFIG
from .language_adapter import LanguageDescriptor

_EXTRA_INSTALL_HINTS: dict[str, str] = {
    "fortran": 'pip install "sciona[fortran]"',
    "c": 'pip install "sciona[c]"',
    "go": 'pip install "sciona[go]"',
}


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


def install_hint_for(language_id: str) -> str | None:
    descriptor = get_descriptor(language_id)
    if descriptor and descriptor.install_hint:
        return descriptor.install_hint
    if descriptor:
        return None
    return _EXTRA_INSTALL_HINTS.get(
        language_id, f'pip install "sciona[{language_id}]"'
    )


__all__ = ["descriptors", "get_descriptor", "install_hint_for", "supported_languages"]
