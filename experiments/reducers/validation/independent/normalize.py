# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import List, Tuple

from .shared import CallEdge, ImportEdge, NormalizedCallEdge, NormalizedImportEdge


def normalize_call_edges(
    module_qualified_name: str,
    edges: List[CallEdge],
) -> List[NormalizedCallEdge]:
    normalized: List[NormalizedCallEdge] = []
    for edge in edges:
        caller = edge.caller or module_qualified_name
        callee = (edge.callee or "").strip()
        callee_qname = edge.callee_qname or None
        if not callee and callee_qname:
            callee = callee_qname.split(".")[-1]
        dynamic = edge.dynamic or not callee
        normalized.append(
            NormalizedCallEdge(
                caller=caller,
                callee=callee,
                callee_qname=callee_qname,
                dynamic=dynamic,
            )
        )
    return normalized


def normalize_import_edges(
    module_qualified_name: str,
    edges: List[ImportEdge],
) -> List[NormalizedImportEdge]:
    normalized: List[NormalizedImportEdge] = []
    for edge in edges:
        source = edge.source_module or module_qualified_name
        target = (edge.target_module or "").strip()
        normalized.append(
            NormalizedImportEdge(
                source_module=source,
                target_module=target,
                dynamic=edge.dynamic,
            )
        )
    return normalized


def normalize_file_edges(
    module_qualified_name: str,
    call_edges: List[CallEdge],
    import_edges: List[ImportEdge],
) -> Tuple[List[NormalizedCallEdge], List[NormalizedImportEdge]]:
    return (
        normalize_call_edges(module_qualified_name, call_edges),
        normalize_import_edges(module_qualified_name, import_edges),
    )
