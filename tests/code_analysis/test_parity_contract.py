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


def test_parity_contract_is_yes_for_all_declared_dimensions() -> None:
    contract = build_parity_contract()
    dimensions = contract["dimensions"]
    for language_claims in dimensions.values():
        assert language_claims == {
            "java": "yes",
            "python": "yes",
            "typescript": "yes",
        }


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
