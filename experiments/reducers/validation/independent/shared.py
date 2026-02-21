# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Definition:
    kind: str
    qualified_name: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class CallEdge:
    caller: str
    callee: str
    callee_qname: str | None
    dynamic: bool
    callee_text: str | None = None


@dataclass(frozen=True)
class ImportEdge:
    source_module: str
    target_module: str
    dynamic: bool
    target_text: str | None = None


@dataclass(frozen=True)
class NormalizedCallEdge:
    caller: str
    callee: str
    callee_qname: str | None
    dynamic: bool
    callee_text: str | None = None


@dataclass(frozen=True)
class NormalizedImportEdge:
    source_module: str
    target_module: str
    dynamic: bool


@dataclass
class FileParseResult:
    language: str
    file_path: str
    module_qualified_name: str
    defs: List[Definition]
    call_edges: List[CallEdge]
    import_edges: List[ImportEdge]
    parse_ok: bool
    error: str | None = None


@dataclass
class GroundTruth:
    in_contract_expected_edges: Set[Tuple[str, str]]
    out_of_contract_edges: Set[Tuple[str, str]]
    parse_ok: bool
    error: str | None = None


@dataclass(frozen=True)
class EdgeRecord:
    caller: str
    callee: str
    callee_qname: str | None


def edge_record_key(edge: EdgeRecord) -> tuple[str, str, str | None]:
    return (edge.caller, edge.callee, edge.callee_qname)


def dedupe_edge_records(edges: List[EdgeRecord]) -> List[EdgeRecord]:
    seen: set[tuple[str, str, str | None]] = set()
    deduped: List[EdgeRecord] = []
    for edge in edges:
        key = edge_record_key(edge)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(edge)
    return deduped


def match_edge(
    sciona_callee: str | None,
    sciona_callee_qname: str | None,
    expected_callee: str,
    expected_qname: str | None,
) -> bool:
    if expected_qname and sciona_callee_qname:
        if sciona_callee_qname == expected_qname:
            return True
    if sciona_callee_qname and expected_qname:
        if sciona_callee_qname.endswith(f".{expected_callee}"):
            return True
    if sciona_callee and expected_callee:
        if sciona_callee == expected_callee:
            return True
    if sciona_callee_qname and expected_callee:
        if sciona_callee_qname.endswith(f".{expected_callee}"):
            return True
    return False
