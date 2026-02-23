# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.core.extract.languages.call_resolution_kernel import (
    CallResolutionOutcome,
    CallResolutionRequest,
    materialize_outcomes,
    resolve_with_adapter,
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
