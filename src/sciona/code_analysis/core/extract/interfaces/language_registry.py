# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Descriptor-first language registry for extraction wiring."""

from __future__ import annotations

from ....config import LANGUAGE_CONFIG
from .language_adapter import AdapterSpecV1, LanguageDescriptor

_EXTRA_INSTALL_HINTS: dict[str, str] = {
    "fortran": 'pip install "sciona[fortran]"',
    "c": 'pip install "sciona[c]"',
    "go": 'pip install "sciona[go]"',
}

_LANGUAGE_METADATA: dict[str, dict[str, object]] = {
    "python": {
        "grammar_name": "python",
        "query_set_version": 1,
        "capability_manifest_key": "python",
    },
    "typescript": {
        "grammar_name": "typescript",
        "query_set_version": 1,
        "capability_manifest_key": "typescript",
    },
    "java": {
        "grammar_name": "java",
        "query_set_version": 1,
        "capability_manifest_key": "java",
    },
    "javascript": {
        "grammar_name": "javascript",
        "query_set_version": 1,
        "capability_manifest_key": "javascript",
    },
}


def descriptors() -> dict[str, LanguageDescriptor]:
    """Return static language descriptors keyed by language id."""
    registered: dict[str, LanguageDescriptor] = {}
    for language_id, config in LANGUAGE_CONFIG.items():
        metadata = _LANGUAGE_METADATA.get(language_id, {})
        registered[language_id] = LanguageDescriptor(
            language_id=language_id,
            extensions=config.extensions,
            callable_types=config.callable_types,
            extractor_factory=config.analyzer_factory,
            module_namer=config.module_namer,
            grammar_name=metadata.get("grammar_name"),
            query_set_version=metadata.get("query_set_version"),
            capability_manifest_key=metadata.get("capability_manifest_key"),
        )
    return registered


def get_descriptor(language_id: str) -> LanguageDescriptor | None:
    return descriptors().get(language_id)


def supported_languages() -> tuple[str, ...]:
    return tuple(sorted(descriptors().keys()))


def optional_languages() -> tuple[str, ...]:
    return tuple(sorted(_EXTRA_INSTALL_HINTS.keys()))


def language_availability() -> dict[str, tuple[str, ...]]:
    installed = supported_languages()
    optional = optional_languages()
    supported = tuple(sorted(set(installed) | set(optional)))
    missing = tuple(sorted(set(optional) - set(installed)))
    return {
        "supported": supported,
        "installed": installed,
        "missing": missing,
    }


def install_hint_for(language_id: str) -> str | None:
    descriptor = get_descriptor(language_id)
    if descriptor and descriptor.install_hint:
        return descriptor.install_hint
    if descriptor:
        return None
    return _EXTRA_INSTALL_HINTS.get(
        language_id, f'pip install "sciona[{language_id}]"'
    )


def descriptor_validation_errors(language_id: str) -> tuple[str, ...]:
    descriptor = get_descriptor(language_id)
    if descriptor is None:
        return (f"descriptor not registered for language '{language_id}'",)
    errors: list[str] = []
    if not descriptor.extensions:
        errors.append("missing file extensions")
    if not descriptor.callable_types:
        errors.append("missing callable_types")
    if descriptor.extractor_factory is None:
        errors.append("missing extractor_factory")
    if descriptor.module_namer is None:
        errors.append("missing module_namer")
    if not descriptor.grammar_name:
        errors.append("missing grammar_name")
    if descriptor.query_set_version is None:
        errors.append("missing query_set_version")
    if not descriptor.capability_manifest_key:
        errors.append("missing capability_manifest_key")
    return tuple(errors)


def assert_descriptor_compliant(language_id: str) -> None:
    errors = descriptor_validation_errors(language_id)
    if not errors:
        return
    joined = "; ".join(errors)
    raise ValueError(f"Invalid language descriptor for '{language_id}': {joined}")


def adapter_spec_v1(language_id: str) -> AdapterSpecV1:
    descriptor = get_descriptor(language_id)
    if descriptor is None:
        raise ValueError(f"descriptor not registered for language '{language_id}'")
    spec = descriptor.to_adapter_spec_v1()
    if spec is None:
        raise ValueError(
            f"Invalid language descriptor for '{language_id}': incomplete AdapterSpecV1"
        )
    return spec


__all__ = [
    "adapter_spec_v1",
    "assert_descriptor_compliant",
    "language_availability",
    "optional_languages",
    "descriptor_validation_errors",
    "descriptors",
    "get_descriptor",
    "install_hint_for",
    "supported_languages",
]
