# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.code_analysis.artifacts.in_repo_static_gate import (
    evaluate_callsite_row_for_persistence,
    normalized_non_accepted_gate_reason,
)


def _row(
    *,
    status: str,
    accepted_callee_id: str | None,
    provenance: str | None,
    drop_reason: str | None,
    candidate_count: int,
) -> tuple:
    return (
        "helper",
        status,
        accepted_callee_id,
        provenance,
        drop_reason,
        candidate_count,
        "terminal",
        None,
        None,
        1,
        1,
        "pkg.alpha",
    )


def test_gate_rejects_zero_candidate_rows() -> None:
    decision = evaluate_callsite_row_for_persistence(
        _row(
            status="dropped",
            accepted_callee_id=None,
            provenance=None,
            drop_reason="no_candidates",
            candidate_count=0,
        ),
        in_repo_callable_ids={"func_alpha"},
    )

    assert decision.persist is False
    assert decision.gate_reason == "no_in_repo_candidate"
    assert decision.raw_drop_reason == "no_candidates"


def test_gate_accepts_in_repo_accepted_rows() -> None:
    decision = evaluate_callsite_row_for_persistence(
        _row(
            status="accepted",
            accepted_callee_id="func_alpha",
            provenance="exact_qname",
            drop_reason=None,
            candidate_count=1,
        ),
        in_repo_callable_ids={"func_alpha"},
    )

    assert decision.persist is True
    assert decision.gate_reason is None
    assert decision.raw_drop_reason is None


def test_gate_rejects_out_of_repo_accepted_rows() -> None:
    decision = evaluate_callsite_row_for_persistence(
        _row(
            status="accepted",
            accepted_callee_id="external_callable",
            provenance="exact_qname",
            drop_reason=None,
            candidate_count=1,
        ),
        in_repo_callable_ids={"func_alpha"},
    )

    assert decision.persist is False
    assert decision.gate_reason == "outside_in_repo_scope"
    assert decision.raw_drop_reason is None


def test_gate_rejects_dropped_rows_with_allowed_drop_reason_as_insufficient_static_evidence() -> None:
    decision = evaluate_callsite_row_for_persistence(
        _row(
            status="dropped",
            accepted_callee_id=None,
            provenance=None,
            drop_reason="unique_without_provenance",
            candidate_count=1,
        ),
        in_repo_callable_ids={"func_alpha"},
    )

    assert decision.persist is False
    assert decision.gate_reason == "insufficient_static_evidence"
    assert decision.raw_drop_reason == "unique_without_provenance"


def test_gate_rejects_invalid_observation_shape() -> None:
    decision = evaluate_callsite_row_for_persistence(
        _row(
            status="accepted",
            accepted_callee_id="func_alpha",
            provenance="unsupported_provenance_value",
            drop_reason=None,
            candidate_count=1,
        ),
        in_repo_callable_ids={"func_alpha"},
    )

    assert decision.persist is False
    assert decision.gate_reason == "invalid_observation_shape"
    assert decision.raw_drop_reason is None


def test_unknown_gate_reason_normalizes_to_invalid_shape() -> None:
    assert (
        normalized_non_accepted_gate_reason("some_future_bucket")
        == "invalid_observation_shape"
    )
