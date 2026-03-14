# SPDX-License-Identifier: MIT

"""TypeScript-specific pre-persist diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_TS_GLOBALS = frozenset(
    {"Promise", "Array", "Object", "String", "Number", "Boolean", "Math", "JSON", "console"}
)


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    if identifier in _TS_GLOBALS or identifier.startswith("console."):
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("typescript_global_pattern",),
        )
    if identifier.startswith(("this.", "super.")):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("typescript_receiver_pattern",),
        )
    if identifier.startswith("@"):
        return DiagnosticClassification(
            bucket="likely_external_dependency",
            reasons=("typescript_package_scope_pattern",),
        )
    return None
