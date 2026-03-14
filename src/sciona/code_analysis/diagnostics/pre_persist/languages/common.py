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
_DYNAMIC_MEMBER_TERMINALS = frozenset(
    {
        "accept",
        "append",
        "call",
        "disconnect",
        "encode",
        "exceptionFactory",
        "feed",
        "filter",
        "find",
        "flat",
        "flatMap",
        "forEach",
        "get_secret_value",
        "includes",
        "items",
        "join",
        "keys",
        "map",
        "match",
        "model_dump",
        "model_dump_json",
        "model_validate",
        "onProcessingEndHook",
        "parse_obj",
        "pop",
        "push",
        "receive_text",
        "reduce",
        "send_json",
        "send_text",
        "slice",
        "some",
        "to_python",
        "values",
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
    terminal = identifier.rsplit(".", 1)[-1]
    if (
        identifier.startswith(("self.", "this.", "cls.", "super."))
        or ".prototype." in identifier
        or identifier.startswith("prototype.")
    ):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("dynamic_receiver_pattern",),
        )
    if _has_repeated_qualified_segment(identifier):
        return DiagnosticClassification(
            bucket="likely_parser_extraction_gap",
            reasons=("repeated_qualified_segment",),
        )
    if terminal in _DYNAMIC_MEMBER_TERMINALS:
        if observation.repo_prefix_matches and observation.callee_kind == "qualified":
            return DiagnosticClassification(
                bucket="likely_unindexed_symbol",
                reasons=("repo_owned_member_terminal",),
            )
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("dynamic_member_terminal",),
        )
    if observation.repo_prefix_matches:
        if observation.callee_kind == "qualified":
            return DiagnosticClassification(
                bucket="likely_unindexed_symbol",
                reasons=("repo_owned_qualified_prefix",),
            )
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("repo_owned_terminal_call_shape",),
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
    if observation.identifier_root and observation.identifier_root in _COMMON_BUILTINS:
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("common_builtin_root",),
        )
    return DiagnosticClassification(
        bucket="likely_unindexed_symbol",
        reasons=("terminal_identifier_without_repo_candidate",),
    )


def _has_repeated_qualified_segment(identifier: str) -> bool:
    parts = [part for part in identifier.split(".") if part]
    if len(parts) < 2:
        return False
    for previous, current in zip(parts, parts[1:]):
        if previous == current:
            return True
    if len(parts) >= 3 and parts[-1] == parts[-2]:
        return True
    if len(parts) >= 3 and parts[-1] == parts[-3]:
        return True
    return False
