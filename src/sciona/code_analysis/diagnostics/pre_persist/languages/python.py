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
_PYTHON_STDLIB_ROOTS = frozenset(
    {
        "collections",
        "datetime",
        "json",
        "os",
        "pathlib",
        "sys",
        "typing",
    }
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
_PYTHON_COLLECTION_MEMBER_TERMINALS = frozenset(
    {
        "append",
        "feed",
        "items",
        "keys",
        "pop",
        "receive_text",
        "send_json",
        "send_text",
        "values",
    }
)


def classify(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification | None:
    identifier = observation.identifier.strip()
    parts = [part for part in identifier.split(".") if part]
    terminal = identifier.rsplit(".", 1)[-1]
    root = observation.identifier_root or identifier.split(".", 1)[0]
    if (
        not _has_repo_ownership_signal(observation)
        and (root in _PYTHON_BUILTINS or root in _PYTHON_STDLIB_ROOTS)
    ):
        return DiagnosticClassification(
            bucket="likely_standard_library_or_builtin",
            reasons=("python_builtin_or_stdlib_root",),
        )
    if identifier.startswith(("self.", "cls.")):
        return DiagnosticClassification(
            bucket="likely_dynamic_dispatch_or_indirect",
            reasons=("python_receiver_pattern",),
        )
    if terminal in _PYTHON_DYNAMIC_MEMBER_TERMINALS:
        if observation.repo_prefix_matches and observation.callee_kind == "qualified":
            owner = parts[-2] if len(parts) >= 2 else ""
            if (
                terminal in _PYTHON_COLLECTION_MEMBER_TERMINALS
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


def _has_repo_ownership_signal(observation: DiagnosticMissObservation) -> bool:
    return bool(
        observation.repo_prefix_matches
        or observation.reachable_repo_prefix_matches
        or observation.reachable_repo_binding
        or observation.repo_hint_overlap
    )
