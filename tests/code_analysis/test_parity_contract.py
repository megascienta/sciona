# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.languages.common.capabilities.parity_contract import (
    build_parity_contract,
)
from sciona.code_analysis.languages.common.capabilities.walker_capabilities import (
    build_walker_capabilities,
)
from sciona.code_analysis.config import LANGUAGE_CONFIG


def test_parity_contract_declared_dimensions_match_expected_matrix() -> None:
    contract = build_parity_contract()
    dimensions = contract["dimensions"]
    languages = tuple(contract["languages"])
    expected = {key: {lang: "yes" for lang in languages} for key in dimensions}
    expected["core_implements_edges"]["python"] = "n/a"
    expected["core_implements_edges"]["javascript"] = "n/a"
    assert dimensions == expected


def test_parity_contract_does_not_declare_kernel_stage_order() -> None:
    contract = build_parity_contract()
    assert "required_resolution_stages" not in contract
    assert "resolution_stage_enforcement" not in contract


def test_parity_contract_languages_match_capabilities_and_config() -> None:
    contract = build_parity_contract()
    expected = set(LANGUAGE_CONFIG)
    assert set(contract["languages"]) == expected
    assert set(build_walker_capabilities()) == expected


def test_parity_contract_documents_java_callable_asymmetry() -> None:
    contract = build_parity_contract()
    asymmetries = contract.get("documented_asymmetries", {})
    java = asymmetries.get("java")
    assert java is not None
    assert tuple(java["callable_types"]) == LANGUAGE_CONFIG["java"].callable_types


def test_parity_contract_documents_python_implements_asymmetry() -> None:
    contract = build_parity_contract()
    asymmetries = contract.get("documented_asymmetries", {})
    python = asymmetries.get("python")
    assert python is not None
    assert python["implements_edges"]["present"] is False


def test_parity_contract_documents_javascript_implements_asymmetry() -> None:
    contract = build_parity_contract()
    asymmetries = contract.get("documented_asymmetries", {})
    javascript = asymmetries.get("javascript")
    assert javascript is not None
    assert javascript["implements_edges"]["present"] is False


def test_parity_contract_declares_parse_diagnostics_parity() -> None:
    contract = build_parity_contract()
    dimension = contract["dimensions"]["parse_diagnostics_and_degraded_analysis"]
    assert dimension == {language: "yes" for language in contract["languages"]}
