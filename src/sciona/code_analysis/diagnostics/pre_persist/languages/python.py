# SPDX-License-Identifier: MIT

"""Python-specific pre-persist diagnostic refinements."""

from __future__ import annotations

from ..models import DiagnosticClassification, DiagnosticMissObservation

_PYTHON_BUILTINS = frozenset(
    {
        "print",
        "len",
        "range",
        "open",
        "min",
        "max",
        "sum",
        "sorted",
        "list",
        "dict",
        "set",
        "tuple",
        "str",
        "int",
        "float",
        "bool",
        "enumerate",
        "zip",
        "isinstance",
        "issubclass",
    }
)
_PYTHON_STDLIB_PREFIXES = (
    "os.",
    "sys.",
    "json.",
    "pathlib.",
    "typing.",
    "collections.",
    "datetime.",
)
_PYTHON_DYNAMIC_MEMBER_TERMINALS = frozenset(
    {
        "append",
        "call",
        "encode",
        "feed",
        "get_secret_value",
        "items",
        "keys",
        "model_dump",
        "model_dump_json",
        "model_validate",
        "parse_obj",
        "pop",
        "receive_text",
        "send_json",
        "send_text",
        "to_python",
        "values",
    }
)


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    terminal = identifier.rsplit(".", 1)[-1]
    if identifier in _PYTHON_BUILTINS or identifier.startswith(_PYTHON_STDLIB_PREFIXES):
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("python_builtin_or_stdlib_pattern",),
        )
    if identifier.startswith(("self.", "cls.")):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("python_receiver_pattern",),
        )
    if terminal in _PYTHON_DYNAMIC_MEMBER_TERMINALS:
        if observation.repo_prefix_matches and observation.callee_kind == "qualified":
            return DiagnosticClassification(
                bucket="likely_unindexed_symbol",
                reasons=("repo_owned_member_terminal",),
            )
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("dynamic_member_terminal",),
        )
    return None
