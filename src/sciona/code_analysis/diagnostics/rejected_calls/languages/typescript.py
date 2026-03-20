# SPDX-License-Identifier: MIT

"""TypeScript-specific rejected-call diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_TS_GLOBALS = frozenset(
    {"Promise", "Array", "Object", "String", "Number", "Boolean", "Math", "JSON", "console"}
)
_TS_DYNAMIC_MEMBER_TERMINALS = frozenset(
    {
        "accept",
        "call",
        "disconnect",
        "entries",
        "exceptionFactory",
        "filter",
        "finally",
        "find",
        "flat",
        "flatMap",
        "forEach",
        "has",
        "includes",
        "join",
        "keys",
        "map",
        "match",
        "onProcessingEndHook",
        "pop",
        "push",
        "reduce",
        "slice",
        "some",
        "values",
    }
)
_TS_COLLECTION_MEMBER_TERMINALS = frozenset(
    {
        "accept",
        "disconnect",
        "entries",
        "filter",
        "find",
        "flat",
        "flatMap",
        "forEach",
        "has",
        "includes",
        "join",
        "keys",
        "map",
        "match",
        "onProcessingEndHook",
        "pop",
        "push",
        "reduce",
        "slice",
        "some",
        "values",
    }
)
_TS_ALWAYS_DYNAMIC_FLUENT_TERMINALS = frozenset(
    {
        "filter",
        "finally",
        "find",
        "flatMap",
        "forEach",
        "includes",
        "map",
        "reduce",
        "slice",
        "some",
    }
)


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    parts = [part for part in identifier.split(".") if part]
    terminal = identifier.rsplit(".", 1)[-1]
    root = observation.identifier_root or identifier.split(".", 1)[0]
    if not _has_repo_ownership_signal(observation) and root in _TS_GLOBALS:
        return DiagnosticClassification(
            bucket="builtin_or_standard_shape",
            reasons=("typescript_global_root",),
        )
    if (
        identifier.startswith(("this.", "super."))
        or ".prototype." in identifier
        or identifier.startswith("prototype.")
    ):
        return DiagnosticClassification(
            bucket="dynamic_or_indirect_shape",
            reasons=("typescript_receiver_pattern",),
        )
    if terminal in _TS_DYNAMIC_MEMBER_TERMINALS:
        if observation.repo_prefix_matches and observation.callee_kind == "qualified":
            owner = parts[-2] if len(parts) >= 2 else ""
            if terminal in _TS_ALWAYS_DYNAMIC_FLUENT_TERMINALS:
                return DiagnosticClassification(
                    bucket="dynamic_or_indirect_shape",
                    reasons=("repo_owned_dynamic_member_terminal",),
                )
            if (
                terminal in _TS_COLLECTION_MEMBER_TERMINALS
                and owner
                and not _looks_type_like_owner(owner)
            ):
                return DiagnosticClassification(
                    bucket="dynamic_or_indirect_shape",
                    reasons=("repo_owned_dynamic_member_terminal",),
                )
            return DiagnosticClassification(
                bucket="unindexed_symbol_shape",
                reasons=("repo_owned_member_terminal",),
            )
        return DiagnosticClassification(
            bucket="dynamic_or_indirect_shape",
            reasons=("dynamic_member_terminal",),
        )
    if identifier.startswith("@"):
        return DiagnosticClassification(
            bucket="external_dependency_shape",
            reasons=("typescript_package_scope_pattern",),
        )
    return None


def _looks_type_like_owner(owner: str) -> bool:
    if not owner:
        return False
    return owner[:1].isupper() or owner.isupper()


def _has_repo_ownership_signal(observation: DiagnosticMissObservation) -> bool:
    return bool(
        observation.repo_prefix_matches
        or observation.reachable_repo_prefix_matches
        or observation.reachable_repo_binding
        or observation.repo_hint_overlap
    )
