# SPDX-License-Identifier: MIT

"""Language-agnostic fallback classifier."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_COMMON_BUILTINS = frozenset(
    {
        "print",
        "len",
        "range",
        "open",
        "min",
        "max",
        "sum",
        "map",
        "filter",
        "sorted",
        "list",
        "dict",
        "set",
        "tuple",
        "str",
        "int",
        "float",
        "bool",
        "Promise",
        "Array",
        "Object",
        "String",
        "Number",
        "Boolean",
        "Math",
        "System",
    }
)


def classify_common(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    identifier = observation.identifier.strip()
    if not identifier or not observation.file_path:
        return DiagnosticClassification(
            bucket="likely_parser_extraction_gap",
            reasons=("missing_identifier_or_file_path",),
        )
    if identifier in _COMMON_BUILTINS:
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("common_builtin_name",),
        )
    if (
        identifier.startswith(("self.", "this.", "cls.", "super."))
        or ".prototype." in identifier
        or identifier.startswith("prototype.")
    ):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("dynamic_receiver_pattern",),
        )
    if "." in identifier:
        first = identifier.split(".", 1)[0]
        if first in {"self", "this", "cls", "super"}:
            return DiagnosticClassification(
                bucket="likely_dynamic_dispatch_or_indirect",
                reasons=("dynamic_receiver_root",),
            )
        if observation.candidate_module_hints:
            return DiagnosticClassification(
                bucket="likely_external_dependency",
                reasons=("qualified_identifier_with_module_hints",),
            )
        return DiagnosticClassification(
            bucket="likely_external_dependency",
            reasons=("qualified_identifier_without_repo_candidate",),
        )
    return DiagnosticClassification(
        bucket="likely_unindexed_symbol",
        reasons=("terminal_identifier_without_repo_candidate",),
    )
