# SPDX-License-Identifier: MIT

"""JavaScript-specific pre-persist diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_JS_GLOBALS = frozenset(
    {"Promise", "Array", "Object", "String", "Number", "Boolean", "Math", "JSON", "console"}
)


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    if identifier in _JS_GLOBALS or identifier.startswith("console."):
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("javascript_global_pattern",),
        )
    if identifier.startswith(("this.", "super.")):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("javascript_receiver_pattern",),
        )
    return None
