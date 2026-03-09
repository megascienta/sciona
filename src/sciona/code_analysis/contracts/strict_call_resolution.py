# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence, cast

from .strict_call_contract import StrictCallDecision, select_strict_call_candidate

STRICT_RESOLUTION_SCALAR_KEYS = (
    "identifiers_total",
    "accepted_identifiers",
    "dropped_identifiers",
)
STRICT_RESOLUTION_COUNTER_KEYS = (
    "accepted_by_provenance",
    "dropped_by_reason",
    "candidate_count_histogram",
)


@dataclass(frozen=True)
class StrictResolvedIdentifier:
    identifier: str
    ordinal: int
    decision: StrictCallDecision


@dataclass(frozen=True)
class StrictResolutionBatch:
    resolutions: tuple[StrictResolvedIdentifier, ...]
    accepted_candidates: tuple[str, ...]
    stats: dict[str, object]


def build_strict_resolution_stats() -> dict[str, object]:
    return {
        "identifiers_total": 0,
        "accepted_identifiers": 0,
        "dropped_identifiers": 0,
        "accepted_by_provenance": Counter(),
        "dropped_by_reason": Counter(),
        "candidate_count_histogram": Counter(),
    }


def record_strict_resolution_decision(
    stats: dict[str, object],
    decision: StrictCallDecision,
    *,
    accepted_provenance: str | None = None,
) -> None:
    stats["identifiers_total"] = int(stats.get("identifiers_total", 0)) + 1
    cast(Counter[int], stats.setdefault("candidate_count_histogram", Counter()))[
        decision.candidate_count
    ] += 1
    if decision.accepted_candidate:
        stats["accepted_identifiers"] = int(stats.get("accepted_identifiers", 0)) + 1
        cast(Counter[str], stats.setdefault("accepted_by_provenance", Counter()))[
            accepted_provenance or str(decision.accepted_provenance)
        ] += 1
        return
    stats["dropped_identifiers"] = int(stats.get("dropped_identifiers", 0)) + 1
    cast(Counter[str], stats.setdefault("dropped_by_reason", Counter()))[
        str(decision.dropped_reason)
    ] += 1


def merge_strict_resolution_stats(
    target: dict[str, object],
    source: Mapping[str, object],
    *,
    stringify_counter_keys: bool = False,
) -> None:
    for key in STRICT_RESOLUTION_SCALAR_KEYS:
        amount = int(source.get(key, 0) or 0)
        if amount:
            target[key] = int(target.get(key, 0) or 0) + amount
    for key in STRICT_RESOLUTION_COUNTER_KEYS:
        bucket = target.setdefault(key, {})
        if not isinstance(bucket, dict):
            bucket = {}
            target[key] = bucket
        values = source.get(key) or {}
        if not isinstance(values, (dict, Counter)):
            continue
        for counter_key, value in values.items():
            if not value:
                continue
            name = str(counter_key) if stringify_counter_keys else counter_key
            bucket[name] = int(bucket.get(name, 0)) + int(value)


def resolve_strict_call_batch(
    identifiers: Sequence[str],
    *,
    symbol_index: Mapping[str, Sequence[str]],
    caller_module: str | None,
    module_lookup: Mapping[str, str],
    candidate_qualified_names: Mapping[str, str] | None = None,
    import_targets: Mapping[str, set[str]],
    expanded_import_targets: Mapping[str, set[str]] | None = None,
    caller_ancestor_modules: set[str] | None = None,
    allow_descendant_scope_for_ambiguous: bool = False,
) -> StrictResolutionBatch:
    expanded_import_targets = expanded_import_targets or import_targets
    caller_ancestor_modules = caller_ancestor_modules or set()
    resolutions: list[StrictResolvedIdentifier] = []
    accepted_candidates: list[str] = []
    ordinal_by_identifier: dict[str, int] = {}
    stats = build_strict_resolution_stats()
    for identifier in identifiers:
        direct_candidates = list(symbol_index.get(identifier) or ())
        fallback_candidates: list[str] = []
        if not direct_candidates and "." in identifier:
            fallback_candidates = list(symbol_index.get(identifier.rsplit(".", 1)[-1]) or ())
        decision = select_strict_call_candidate(
            identifier=identifier,
            direct_candidates=direct_candidates,
            fallback_candidates=fallback_candidates,
            caller_module=caller_module,
            module_lookup=module_lookup,
            candidate_qualified_names=candidate_qualified_names,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            caller_ancestor_modules=caller_ancestor_modules,
            allow_descendant_scope_for_ambiguous=allow_descendant_scope_for_ambiguous,
        )
        ordinal = ordinal_by_identifier.get(identifier, 0) + 1
        ordinal_by_identifier[identifier] = ordinal
        resolutions.append(
            StrictResolvedIdentifier(
                identifier=identifier,
                ordinal=ordinal,
                decision=decision,
            )
        )
        record_strict_resolution_decision(stats, decision)
        if decision.accepted_candidate:
            accepted_candidates.append(decision.accepted_candidate)
    return StrictResolutionBatch(
        resolutions=tuple(resolutions),
        accepted_candidates=tuple(accepted_candidates),
        stats=stats,
    )


__all__ = [
    "StrictResolvedIdentifier",
    "StrictResolutionBatch",
    "build_strict_resolution_stats",
    "merge_strict_resolution_stats",
    "record_strict_resolution_decision",
    "resolve_strict_call_batch",
]
