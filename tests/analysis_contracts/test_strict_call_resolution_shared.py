# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from sciona.code_analysis.analysis_contracts import (
    StrictCallDecision,
    build_strict_resolution_stats,
    merge_strict_resolution_stats,
    record_strict_resolution_decision,
    resolve_strict_call_batch,
)


def test_resolve_strict_call_batch_tracks_ordinals_and_stats() -> None:
    batch = resolve_strict_call_batch(
        ["helper", "helper", "missing"],
        symbol_index={"helper": ["pkg.mod.helper"]},
        caller_module="pkg.mod",
        module_lookup={"pkg.mod.helper": "pkg.mod"},
        import_targets={"pkg.mod": set()},
        caller_ancestor_modules=set(),
    )

    assert [item.ordinal for item in batch.resolutions] == [1, 2, 1]
    assert list(batch.accepted_candidates) == ["pkg.mod.helper", "pkg.mod.helper"]
    assert batch.stats["identifiers_total"] == 3
    assert batch.stats["accepted_identifiers"] == 2
    assert batch.stats["dropped_identifiers"] == 1
    assert batch.stats["candidate_count_histogram"] == {1: 2, 0: 1}
    assert batch.stats["accepted_by_provenance"] == {"module_scoped": 2}
    assert batch.stats["dropped_by_reason"] == {"no_candidates": 1}


def test_resolve_strict_call_batch_uses_candidate_qname_mapping() -> None:
    batch = resolve_strict_call_batch(
        ["pkg.alpha.service.helper"],
        symbol_index={"pkg.alpha.service.helper": ["func_alpha"]},
        caller_module="pkg.alpha.task",
        module_lookup={"func_alpha": "pkg.alpha.service"},
        candidate_qualified_names={"func_alpha": "pkg.alpha.service.helper"},
        import_targets={"pkg.alpha.task": {"pkg.alpha.service"}},
        caller_ancestor_modules={"pkg.alpha"},
    )

    assert list(batch.accepted_candidates) == ["func_alpha"]
    assert batch.stats["accepted_by_provenance"] == {"exact_qname": 1}


def test_strict_resolution_stats_helpers_record_and_merge() -> None:
    first = build_strict_resolution_stats()
    second = build_strict_resolution_stats()

    record_strict_resolution_decision(
        first,
        StrictCallDecision(
            accepted_candidate="pkg.mod.helper",
            accepted_provenance="module_scoped",
            dropped_reason=None,
            candidate_count=1,
        ),
    )
    record_strict_resolution_decision(
        second,
        StrictCallDecision(
            accepted_candidate=None,
            accepted_provenance=None,
            dropped_reason="no_candidates",
            candidate_count=0,
        ),
    )

    target: dict[str, object] = {}
    merge_strict_resolution_stats(target, first, stringify_counter_keys=True)
    merge_strict_resolution_stats(target, second, stringify_counter_keys=True)

    assert target["identifiers_total"] == 2
    assert target["accepted_identifiers"] == 1
    assert target["dropped_identifiers"] == 1
    assert target["accepted_by_provenance"] == {"module_scoped": 1}
    assert target["dropped_by_reason"] == {"no_candidates": 1}
    assert target["candidate_count_histogram"] == {"1": 1, "0": 1}
