# SPDX-License-Identifier: MIT

"""Python-specific pre-persist diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_PYTHON_BUILTINS = frozenset(
    {"print", "len", "range", "open", "enumerate", "zip", "isinstance", "issubclass"}
)
_PYTHON_STDLIB_PREFIXES = ("os.", "sys.", "json.", "pathlib.", "typing.", "collections.")


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    if identifier in _PYTHON_BUILTINS or identifier.startswith(_PYTHON_STDLIB_PREFIXES):
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("python_builtin_or_stdlib_pattern",),
        )
    return None
