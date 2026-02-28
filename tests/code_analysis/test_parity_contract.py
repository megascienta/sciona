# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.languages.call_resolution_kernel import (
    REQUIRED_RESOLUTION_STAGES,
)
from sciona.code_analysis.core.extract.languages.parity_contract import (
    build_parity_contract,
)
from sciona.code_analysis.core.extract.languages.walker_capabilities import (
    build_walker_capabilities,
)
from sciona.code_analysis.config import LANGUAGE_CONFIG


def test_parity_contract_declared_dimensions_match_expected_matrix() -> None:
    contract = build_parity_contract()
    dimensions = contract["dimensions"]
    expected = {
        key: {"java": "yes", "python": "yes", "typescript": "yes"}
        for key in dimensions
    }
    expected["core_implements_edges"] = {
        "java": "yes",
        "python": "n/a",
        "typescript": "yes",
    }
    assert dimensions == expected


def test_parity_contract_stage_order_matches_kernel_contract() -> None:
    contract = build_parity_contract()
    assert tuple(contract["required_resolution_stages"]) == REQUIRED_RESOLUTION_STAGES


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
