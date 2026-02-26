# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass

from .independent.shared import CallEdge, ImportEdge


@dataclass(frozen=True)
class CanonicalRawCallEdge:
    caller: str
    callee: str
    callee_qname: str | None
    dynamic: bool
    callee_text: str | None


@dataclass(frozen=True)
class CanonicalRawImportEdge:
    source_module: str
    target_module: str
    dynamic: bool
    target_text: str | None


def canonicalize_call_edge(edge: CallEdge) -> CanonicalRawCallEdge:
    return CanonicalRawCallEdge(
        caller=(edge.caller or "").strip(),
        callee=(edge.callee or "").strip(),
        callee_qname=((edge.callee_qname or "").strip() or None),
        dynamic=bool(edge.dynamic),
        callee_text=((edge.callee_text or "").strip() or None),
    )


def canonicalize_import_edge(edge: ImportEdge) -> CanonicalRawImportEdge:
    return canonicalize_import_edge_with_default(edge, default_source_module="")


def canonicalize_import_edge_with_default(
    edge: ImportEdge,
    *,
    default_source_module: str,
) -> CanonicalRawImportEdge:
    return CanonicalRawImportEdge(
        source_module=((edge.source_module or "").strip() or default_source_module),
        target_module=(edge.target_module or "").strip(),
        dynamic=bool(edge.dynamic),
        target_text=((edge.target_text or "").strip() or None),
    )


def call_key(edge: CanonicalRawCallEdge) -> tuple[str, str]:
    return edge.caller, edge.callee


def validate_call_schema(edge: CanonicalRawCallEdge) -> list[str]:
    errors: list[str] = []
    if not edge.caller:
        errors.append("missing caller")
    if not edge.callee:
        errors.append("missing callee")
    if not isinstance(edge.dynamic, bool):
        errors.append("dynamic must be bool")
    return errors


def validate_import_schema(edge: CanonicalRawImportEdge) -> list[str]:
    errors: list[str] = []
    if not edge.source_module:
        errors.append("missing source_module")
    if not edge.target_module:
        errors.append("missing target_module")
    if not isinstance(edge.dynamic, bool):
        errors.append("dynamic must be bool")
    return errors


__all__ = [
    "CanonicalRawCallEdge",
    "CanonicalRawImportEdge",
    "canonicalize_call_edge",
    "canonicalize_import_edge",
    "canonicalize_import_edge_with_default",
    "call_key",
    "validate_call_schema",
    "validate_import_schema",
]
