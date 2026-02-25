# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.languages.call_resolution_kernel import (
    REQUIRED_RESOLUTION_STAGES,
)
from sciona.code_analysis.core.extract.languages.parity_contract import (
    build_parity_contract,
)


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

