# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.call_resolution_kernel import (
    REQUIRED_RESOLUTION_STAGES,
)
from sciona.code_analysis.languages.common.support.parity_contract import (
    build_parity_contract,
)
from sciona.code_analysis.languages.common.support.walker_capabilities import (
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


def test_parity_contract_stage_order_matches_kernel_contract() -> None:
    contract = build_parity_contract()
    assert tuple(contract["required_resolution_stages"]) == REQUIRED_RESOLUTION_STAGES


def test_parity_contract_declares_stage_enforcement_ownership() -> None:
    contract = build_parity_contract()
    enforcement = contract["resolution_stage_enforcement"]
    assert enforcement == {
        "owner": "language_adapters_via_shared_kernel",
        "strict_call_gate_role": "final_materialization_only",
    }


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
