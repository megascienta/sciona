# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import pytest

from sciona.code_analysis.core.extract.languages.call_resolution_kernel import (
    CallResolutionOutcome,
    CallResolutionRequest,
    REQUIRED_RESOLUTION_STAGES,
    materialize_outcomes,
    resolve_with_adapter,
    validate_stage_order,
)


class _EmptyAdapter:
    def resolve(self, request: CallResolutionRequest):
        del request
        return []


def test_resolve_with_adapter_emits_terminal_fallback_outcome() -> None:
    outcomes = resolve_with_adapter(
        [CallResolutionRequest(terminal="run", callee_text="run")],
        _EmptyAdapter(),
    )
    assert outcomes == [
        CallResolutionOutcome(candidate_qname="run", provenance="terminal_fallback")
    ]


def test_materialize_outcomes_filters_by_provenance_allowlist() -> None:
    outcomes = [
        CallResolutionOutcome(
            candidate_qname="repo.pkg.Service.run", provenance="exact_qname"
        ),
        CallResolutionOutcome(candidate_qname="run", provenance="terminal_fallback"),
        CallResolutionOutcome(
            candidate_qname="repo.pkg.util.helper", provenance="import_narrowed"
        ),
    ]
    assert materialize_outcomes(outcomes) == [
        "repo.pkg.Service.run",
        "repo.pkg.util.helper",
    ]


def test_validate_stage_order_accepts_required_contract() -> None:
    validate_stage_order(REQUIRED_RESOLUTION_STAGES)


def test_validate_stage_order_rejects_mismatched_contract() -> None:
    with pytest.raises(ValueError):
        validate_stage_order(("module_scoped_fallback",))
