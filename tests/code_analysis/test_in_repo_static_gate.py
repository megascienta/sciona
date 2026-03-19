# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.code_analysis.artifacts.in_repo_static_gate import (
    evaluate_callsite_row_for_persistence,
    normalized_pre_persist_bucket,
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
    assert decision.rejection_bucket == "no_in_repo_candidate"


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
    assert decision.rejection_bucket is None


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
    assert decision.rejection_bucket == "accepted_outside_in_repo"


def test_gate_accepts_dropped_rows_with_allowed_drop_reason() -> None:
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

    assert decision.persist is True
    assert decision.rejection_bucket is None


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
    assert decision.rejection_bucket == "invalid_observation_shape"


def test_unknown_pre_persist_bucket_normalizes_to_invalid_shape() -> None:
    assert normalized_pre_persist_bucket("some_future_bucket") == "invalid_observation_shape"
