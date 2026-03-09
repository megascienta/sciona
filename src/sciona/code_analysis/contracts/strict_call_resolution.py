# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence, cast

from .strict_call_contract import StrictCallDecision, select_strict_call_candidate


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
    stats: dict[str, object] = {
        "identifiers_total": 0,
        "accepted_identifiers": 0,
        "dropped_identifiers": 0,
        "accepted_by_provenance": Counter(),
        "dropped_by_reason": Counter(),
        "candidate_count_histogram": Counter(),
    }
    for identifier in identifiers:
        stats["identifiers_total"] = int(stats["identifiers_total"]) + 1
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
        cast(Counter[int], stats["candidate_count_histogram"])[decision.candidate_count] += 1
        ordinal = ordinal_by_identifier.get(identifier, 0) + 1
        ordinal_by_identifier[identifier] = ordinal
        resolutions.append(
            StrictResolvedIdentifier(
                identifier=identifier,
                ordinal=ordinal,
                decision=decision,
            )
        )
        if decision.accepted_candidate:
            accepted_candidates.append(decision.accepted_candidate)
            stats["accepted_identifiers"] = int(stats["accepted_identifiers"]) + 1
            cast(Counter[str], stats["accepted_by_provenance"])[
                str(decision.accepted_provenance)
            ] += 1
            continue
        stats["dropped_identifiers"] = int(stats["dropped_identifiers"]) + 1
        cast(Counter[str], stats["dropped_by_reason"])[str(decision.dropped_reason)] += 1
    return StrictResolutionBatch(
        resolutions=tuple(resolutions),
        accepted_candidates=tuple(accepted_candidates),
        stats=stats,
    )
__all__ = [
    "StrictResolvedIdentifier",
    "StrictResolutionBatch",
    "resolve_strict_call_batch",
]
