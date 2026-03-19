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
    in_scope_candidate_count: int = 0
    candidate_module_hints: tuple[str, ...] = ()


def select_strict_call_candidate(
    *,
    identifier: str,
    direct_candidates: Sequence[str],
    fallback_candidates: Sequence[str],
    caller_module: str | None,
    module_lookup: Mapping[str, str],
    candidate_qualified_names: Mapping[str, str] | None = None,
    import_targets: Mapping[str, set[str]],
    expanded_import_targets: Mapping[str, set[str]] | None = None,
    caller_ancestor_modules: set[str] | None = None,
    allow_descendant_scope_for_ambiguous: bool = False,
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
            in_scope_candidate_count=0,
            candidate_module_hints=(),
        )

    candidate_module_hints = _candidate_module_hints(
        candidates=candidates,
        module_lookup=module_lookup,
    )

    if "." in identifier:
        exact_matches = []
        for candidate in candidates:
            candidate_qname = (candidate_qualified_names or {}).get(candidate, candidate)
            if candidate_qname == identifier:
                exact_matches.append(candidate)
        if len(exact_matches) == 1:
            return StrictCallDecision(
                accepted_candidate=exact_matches[0],
                accepted_provenance="exact_qname",
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
            )
        if len(exact_matches) > 1:
            identifier_module = identifier.rsplit(".", 1)[0]
            module_exact = [
                candidate
                for candidate in exact_matches
                if module_lookup.get(candidate) == identifier_module
            ]
            if len(module_exact) == 1:
                return StrictCallDecision(
                    accepted_candidate=module_exact[0],
                    accepted_provenance="exact_qname",
                    dropped_reason=None,
                    candidate_count=candidate_count,
                    in_scope_candidate_count=1,
                    candidate_module_hints=candidate_module_hints,
                )

    if len(candidates) == 1:
        candidate = candidates[0]
        candidate_qname = (candidate_qualified_names or {}).get(candidate, candidate)
        allowed_modules = set(import_targets.get(caller_module or "", set()))
        provenance_scope = set(
            (expanded_import_targets or import_targets).get(caller_module or "", set())
        )
        if caller_module:
            allowed_modules.add(caller_module)
            provenance_scope.add(caller_module)
        if "." in identifier and _is_constructor_proxy_match(
            identifier=identifier, candidate_qname=candidate_qname
        ):
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="exact_qname",
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
            )
        if "." in identifier and _has_index_proxy_qname_match(
            identifier=identifier,
            candidate_qname=candidate_qname,
        ):
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="exact_qname",
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
            )
        candidate_module = _candidate_module(
            candidate=candidate,
            module_lookup=module_lookup,
            scope_modules=provenance_scope,
        )
        if direct_candidates and "." in identifier:
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="exact_qname",
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
            )
        if caller_module and candidate_module == caller_module:
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="module_scoped",
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
            )
        if candidate_module and caller_ancestor_modules and candidate_module in caller_ancestor_modules:
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance="import_narrowed",
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
            )
        if caller_module and candidate_module:
            if _in_allowed_module_scope(
                candidate_module=candidate_module,
                allowed_modules=provenance_scope,
            ):
                return StrictCallDecision(
                    accepted_candidate=candidate,
                    accepted_provenance="import_narrowed",
                    dropped_reason=None,
                    candidate_count=candidate_count,
                    in_scope_candidate_count=1,
                    candidate_module_hints=candidate_module_hints,
                )
        return StrictCallDecision(
            accepted_candidate=None,
            accepted_provenance=None,
            dropped_reason="unique_without_provenance",
            candidate_count=candidate_count,
            in_scope_candidate_count=0,
            candidate_module_hints=candidate_module_hints,
        )

    if not caller_module:
        return StrictCallDecision(
            accepted_candidate=None,
            accepted_provenance=None,
            dropped_reason="ambiguous_no_caller_module",
            candidate_count=candidate_count,
            in_scope_candidate_count=0,
            candidate_module_hints=candidate_module_hints,
        )

    allowed_modules = set(import_targets.get(caller_module, set()))
    allowed_modules.add(caller_module)
    if caller_ancestor_modules:
        allowed_modules.update(caller_ancestor_modules)
    narrowed = []
    for candidate in candidates:
        candidate_module = _candidate_module(
            candidate=candidate,
            module_lookup=module_lookup,
            scope_modules=allowed_modules,
        )
        if _in_allowed_module_scope(
            candidate_module=candidate_module,
            allowed_modules=allowed_modules,
            allow_descendants=allow_descendant_scope_for_ambiguous,
        ):
            narrowed.append(candidate)
    if len(narrowed) == 1:
        return StrictCallDecision(
            accepted_candidate=narrowed[0],
            accepted_provenance="import_narrowed",
            dropped_reason=None,
            candidate_count=candidate_count,
            in_scope_candidate_count=1,
            candidate_module_hints=candidate_module_hints,
        )
    if len(narrowed) > 1 and "." in identifier:
        tail_matches = []
        for candidate in narrowed:
            candidate_qname = (candidate_qualified_names or {}).get(candidate, candidate)
            if _has_structural_tail_match(
                identifier=identifier,
                candidate_qname=candidate_qname,
            ):
                tail_matches.append(candidate)
        if len(tail_matches) == 1:
            candidate = tail_matches[0]
            candidate_module = _candidate_module(
                candidate=candidate,
                module_lookup=module_lookup,
                scope_modules=allowed_modules,
            )
            provenance = (
                "module_scoped"
                if caller_module and candidate_module == caller_module
                else "import_narrowed"
            )
            return StrictCallDecision(
                accepted_candidate=candidate,
                accepted_provenance=provenance,
                dropped_reason=None,
                candidate_count=candidate_count,
                in_scope_candidate_count=1,
                candidate_module_hints=candidate_module_hints,
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
        in_scope_candidate_count=len(narrowed),
        candidate_module_hints=candidate_module_hints,
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


def _in_allowed_module_scope(
    *,
    candidate_module: str | None,
    allowed_modules: set[str],
    allow_descendants: bool = True,
) -> bool:
    if not candidate_module:
        return False
    for allowed in allowed_modules:
        if candidate_module == allowed:
            return True
        if allow_descendants and candidate_module.startswith(f"{allowed}."):
            return True
    return False


def _candidate_module_hints(
    *,
    candidates: Sequence[str],
    module_lookup: Mapping[str, str],
    limit: int = 8,
) -> tuple[str, ...]:
    modules: list[str] = []
    for candidate in candidates:
        module = module_lookup.get(candidate)
        if not module:
            continue
        modules.append(module)
    if not modules:
        return ()
    unique_modules = sorted(set(modules))
    return tuple(unique_modules[:limit])


def _is_constructor_proxy_match(*, identifier: str, candidate_qname: str) -> bool:
    if not identifier or not candidate_qname:
        return False
    if not candidate_qname.startswith(f"{identifier}."):
        return False
    suffix = candidate_qname[len(identifier) + 1 :]
    return suffix in {"__new__", "__init__", "new", "constructor"}


def _has_structural_tail_match(*, identifier: str, candidate_qname: str) -> bool:
    identifier_parts = [part for part in identifier.split(".") if part]
    candidate_parts = [part for part in candidate_qname.split(".") if part]
    if len(identifier_parts) < 3 or len(candidate_parts) < 3:
        return False
    return candidate_parts[-3:] == identifier_parts[-3:]


def _has_index_proxy_qname_match(*, identifier: str, candidate_qname: str) -> bool:
    if not identifier or not candidate_qname:
        return False
    return _collapse_index_proxy_qname(identifier) == _collapse_index_proxy_qname(
        candidate_qname
    )


def _collapse_index_proxy_qname(value: str) -> tuple[str, ...]:
    parts = [part for part in value.split(".") if part]
    if not parts:
        return ()
    collapsed: list[str] = []
    last_index = len(parts) - 1
    for idx, part in enumerate(parts):
        if idx != last_index and part == "index":
            continue
        collapsed.append(part)
    return tuple(collapsed)


__all__ = ["StrictCallDecision", "select_strict_call_candidate"]
