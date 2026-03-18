# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Call extraction package exports."""

from __future__ import annotations

from .extract import (
    _argument_count,
    _call_query_source,
    _call_target_from_call_node,
    _collect_call_targets_query,
    _compile_call_query,
    _compile_call_query_cached,
    _compile_call_query_for_types,
    _compile_terminal_identifier_query_for_language,
    _has_ancestor_in_set,
    _language_signature,
    _query_call_nodes,
    _terminal_identifier_query,
    collect_call_identifiers,
    collect_call_targets,
    get_language,
)
from .queries import normalize_call_identifiers
from .types import (
    CallExtractionRecord,
    CallTarget,
    CallTargetIR,
    PrePersistObservation,
    QualifiedCallIR,
    ReceiverCallIR,
    TerminalCallIR,
)

__all__ = [
    "CallExtractionRecord",
    "CallTarget",
    "CallTargetIR",
    "PrePersistObservation",
    "QualifiedCallIR",
    "ReceiverCallIR",
    "TerminalCallIR",
    "_argument_count",
    "_call_query_source",
    "_call_target_from_call_node",
    "_collect_call_targets_query",
    "_compile_call_query",
    "_compile_call_query_cached",
    "_compile_call_query_for_types",
    "_compile_terminal_identifier_query_for_language",
    "_has_ancestor_in_set",
    "_language_signature",
    "_query_call_nodes",
    "_terminal_identifier_query",
    "collect_call_identifiers",
    "collect_call_targets",
    "get_language",
    "normalize_call_identifiers",
]
