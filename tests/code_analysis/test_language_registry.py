# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.contracts.language_registry import (
    adapter_spec_v1,
    descriptor_validation_errors,
    descriptors,
    get_descriptor,
    install_hint_for,
    supported_languages,
)


def test_language_registry_contains_default_languages() -> None:
    registered = descriptors()
    assert {"python", "typescript", "java", "javascript"}.issubset(registered.keys())


def test_get_descriptor_returns_extension_data() -> None:
    descriptor = get_descriptor("python")
    assert descriptor is not None
    assert ".py" in descriptor.extensions
    assert descriptor.grammar_name == "python"
    assert descriptor.query_set_version == 1
    assert descriptor.capability_manifest_key == "python"
    assert descriptor.extractor_factory is not None


def test_supported_languages_is_sorted() -> None:
    languages = supported_languages()
    assert languages == tuple(sorted(languages))


def test_install_hint_for_extra_language() -> None:
    assert install_hint_for("fortran") == 'pip install "sciona[fortran]"'


def test_descriptor_validation_errors_unknown_language() -> None:
    errors = descriptor_validation_errors("unknown_lang")
    assert errors
    assert "not registered" in errors[0]


def test_descriptor_validation_accepts_builtin_languages() -> None:
    assert descriptor_validation_errors("python") == ()
    assert descriptor_validation_errors("typescript") == ()
    assert descriptor_validation_errors("java") == ()


def test_adapter_spec_v1_available_for_builtin_language() -> None:
    spec = adapter_spec_v1("python")
    assert spec.language_id == "python"
    assert spec.grammar_name == "python"
    assert spec.query_set_version == 1
