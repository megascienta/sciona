# SPDX-License-Identifier: MIT

"""JavaScript-specific pre-persist diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_JS_GLOBALS = frozenset(
    {"Promise", "Array", "Object", "String", "Number", "Boolean", "Math", "JSON", "console"}
)
_JS_DYNAMIC_MEMBER_TERMINALS = frozenset(
    {
        "call",
        "filter",
        "find",
        "flat",
        "flatMap",
        "forEach",
        "includes",
        "join",
        "map",
        "match",
        "pop",
        "push",
        "reduce",
        "slice",
        "some",
    }
)
_JS_COLLECTION_MEMBER_TERMINALS = frozenset(
    {
        "filter",
        "find",
        "flat",
        "flatMap",
        "forEach",
        "includes",
        "join",
        "map",
        "match",
        "pop",
        "push",
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
    if root in _JS_GLOBALS:
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("javascript_global_root",),
        )
    if (
        identifier.startswith(("this.", "super."))
        or ".prototype." in identifier
        or identifier.startswith("prototype.")
    ):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("javascript_receiver_pattern",),
        )
    if terminal in _JS_DYNAMIC_MEMBER_TERMINALS:
        if observation.repo_prefix_matches and observation.callee_kind == "qualified":
            owner = parts[-2] if len(parts) >= 2 else ""
            if (
                terminal in _JS_COLLECTION_MEMBER_TERMINALS
                and owner
                and not _looks_type_like_owner(owner)
            ):
                return DiagnosticClassification(
                    bucket="likely_dynamic_dispatch_or_indirect",
                    reasons=("repo_owned_dynamic_member_terminal",),
                )
            return DiagnosticClassification(
                bucket="likely_unindexed_symbol",
                reasons=("repo_owned_member_terminal",),
            )
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("dynamic_member_terminal",),
        )
    return None


def _looks_type_like_owner(owner: str) -> bool:
    if not owner:
        return False
    return owner[:1].isupper() or owner.isupper()
