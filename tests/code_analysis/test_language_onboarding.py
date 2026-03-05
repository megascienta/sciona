# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.language_adapter import LanguageDescriptor
from sciona.code_analysis.languages.onboarding import validate_language_onboarding


def _descriptor() -> LanguageDescriptor:
    return LanguageDescriptor(
        language_id="rust",
        extensions=(".rs",),
        callable_types=("callable",),
        extractor_factory=lambda: object(),  # type: ignore[arg-type]
        module_namer=lambda _repo_root, snapshot: snapshot.record.relative_path.as_posix(),
        grammar_name="rust",
        query_set_version=1,
        capability_manifest_key="rust",
    )


def test_validate_language_onboarding_success() -> None:
    result = validate_language_onboarding(
        _descriptor(),
        capability_keys={"python", "typescript", "java", "rust"},
        declared_parity_dimensions={"structural_nodes_edges_contract"},
        required_parity_dimensions={"structural_nodes_edges_contract"},
    )
    assert result.valid is True
    assert result.errors == ()


def test_validate_language_onboarding_reports_missing_capability_and_parity() -> None:
    result = validate_language_onboarding(
        _descriptor(),
        capability_keys={"python", "typescript", "java"},
        declared_parity_dimensions=set(),
        required_parity_dimensions={"structural_nodes_edges_contract"},
    )
    assert result.valid is False
    assert any("capability_manifest_key" in item for item in result.errors)
    assert any("missing parity dimensions" in item for item in result.errors)
