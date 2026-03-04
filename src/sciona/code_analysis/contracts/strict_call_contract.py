# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class StrictCallDecision:
    accepted_candidate: str | None
    accepted_provenance: str | None
    dropped_reason: str | None
    candidate_count: int


def select_strict_call_candidate(
    *,
    identifier: str,
    direct_candidates: Sequence[str],
    fallback_candidates: Sequence[str],
    caller_module: str | None,
    module_lookup: Mapping[str, str],
    import_targets: Mapping[str, set[str]],
) -> StrictCallDecision:
    """Apply contract-strict accept_if_single behavior for call candidates."""
    raw_candidates = list(direct_candidates) or list(fallback_candidates)
    candidates = list(dict.fromkeys(raw_candidates))
    candidate_count = len(candidates)
    if not candidates:
        return StrictCallDecision(
            accepted_candidate=None,
            accepted_provenance=None,
            dropped_reason="no_candidates",
            candidate_count=0,
        )

    if "." in identifier:
        exact_matches = [candidate for candidate in candidates if candidate == identifier]
        if len(exact_matches) == 1:
            return StrictCallDecision(
                accepted_candidate=exact_matches[0],
                accepted_provenance="exact_qname",
                dropped_reason=None,
                candidate_count=candidate_count,
            )

    if len(candidates) == 1:
        candidate = candidates[0]
        allowed_modules = set(import_targets.get(caller_module or "", set()))
        if caller_module:
            allowed_modules.add(caller_module)
        candidate_module = _candidate_module(
            candidate=candidate,
            module_lookup=module_lookup,
            scope_modules=allowed_modules,
        )
        if direct_candidates and "." in identifier:
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="exact_qname",
                dropped_reason=None,
                candidate_count=candidate_count,
            )
        if caller_module and candidate_module == caller_module:
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="module_scoped",
                dropped_reason=None,
                candidate_count=candidate_count,
            )
        if caller_module and candidate_module:
            if candidate_module in allowed_modules:
                return StrictCallDecision(
                    accepted_candidate=candidate,
                    accepted_provenance="import_narrowed",
                    dropped_reason=None,
                    candidate_count=candidate_count,
                )
        return StrictCallDecision(
            accepted_candidate=None,
            accepted_provenance=None,
            dropped_reason="unique_without_provenance",
            candidate_count=candidate_count,
        )

    if not caller_module:
        return StrictCallDecision(
            accepted_candidate=None,
            accepted_provenance=None,
            dropped_reason="ambiguous_no_caller_module",
            candidate_count=candidate_count,
        )

    allowed_modules = set(import_targets.get(caller_module, set()))
    allowed_modules.add(caller_module)
    narrowed = []
    for candidate in candidates:
        candidate_module = _candidate_module(
            candidate=candidate,
            module_lookup=module_lookup,
            scope_modules=allowed_modules,
        )
        if candidate_module in allowed_modules:
            narrowed.append(candidate)
    if len(narrowed) == 1:
        return StrictCallDecision(
            accepted_candidate=narrowed[0],
            accepted_provenance="import_narrowed",
            dropped_reason=None,
            candidate_count=candidate_count,
        )
    if not narrowed:
        dropped_reason = "ambiguous_no_in_scope_candidate"
    else:
        dropped_reason = "ambiguous_multiple_in_scope_candidates"
    return StrictCallDecision(
        accepted_candidate=None,
        accepted_provenance=None,
        dropped_reason=dropped_reason,
        candidate_count=candidate_count,
    )


def _candidate_module(
    *,
    candidate: str,
    module_lookup: Mapping[str, str],
    scope_modules: set[str],
) -> str | None:
    module = module_lookup.get(candidate)
    if module:
        return module
    for scope in sorted(scope_modules, key=len, reverse=True):
        if candidate == scope or candidate.startswith(f"{scope}."):
            return scope
    return None


__all__ = ["StrictCallDecision", "select_strict_call_candidate"]
