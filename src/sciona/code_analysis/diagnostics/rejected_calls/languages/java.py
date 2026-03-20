# SPDX-License-Identifier: MIT

"""Java-specific rejected-call diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_JAVA_STDLIB_ROOTS = frozenset(
    {
        "Collections",
        "List",
        "Map",
        "Set",
        "System",
        "java",
        "javax",
    }
)


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    root = observation.identifier_root or identifier.split(".", 1)[0]
    if not _has_repo_ownership_signal(observation) and root in _JAVA_STDLIB_ROOTS:
        return DiagnosticClassification(
            bucket="builtin_or_standard_shape",
            reasons=("java_stdlib_root",),
        )
    return None


def _has_repo_ownership_signal(observation: DiagnosticMissObservation) -> bool:
    return bool(
        observation.repo_prefix_matches
        or observation.reachable_repo_prefix_matches
        or observation.reachable_repo_binding
        or observation.repo_hint_overlap
    )
