# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.language_registry import (
    descriptors,
    get_descriptor,
    supported_languages,
)


def test_language_registry_contains_default_languages() -> None:
    registered = descriptors()
    assert {"python", "typescript", "java"}.issubset(registered.keys())


def test_get_descriptor_returns_extension_data() -> None:
    descriptor = get_descriptor("python")
    assert descriptor is not None
    assert ".py" in descriptor.extensions


def test_supported_languages_is_sorted() -> None:
    languages = supported_languages()
    assert languages == tuple(sorted(languages))
