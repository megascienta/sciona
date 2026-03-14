# SPDX-License-Identifier: MIT

"""Java-specific pre-persist diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_JAVA_STDLIB_PREFIXES = ("java.", "javax.", "System.", "Collections.", "List.", "Map.", "Set.")


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    if identifier.startswith(_JAVA_STDLIB_PREFIXES):
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("java_stdlib_pattern",),
        )
    return None
