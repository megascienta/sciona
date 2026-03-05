# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Builder that materializes AnalysisResult from structural IR records."""

from __future__ import annotations

from ..normalize.model import AnalysisResult, CallRecord, EdgeRecord, SemanticNodeRecord
from .structural_ir import IRCall, IREdge, IRNode


def build_analysis_result(
    *,
    nodes: list[IRNode],
    edges: list[IREdge],
    calls: list[IRCall],
    diagnostics: dict[str, object],
) -> AnalysisResult:
    return AnalysisResult(
        nodes=[
            SemanticNodeRecord(
                language=node.language,
                node_type=node.node_type,
                qualified_name=node.qualified_name,
                display_name=node.display_name,
                file_path=node.file_path,
                start_line=node.start_line,
                end_line=node.end_line,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                file_id=node.file_id,
                metadata=node.metadata,
            )
            for node in nodes
        ],
        edges=[
            EdgeRecord(
                src_language=edge.src_language,
                src_node_type=edge.src_node_type,
                src_qualified_name=edge.src_qualified_name,
                dst_language=edge.dst_language,
                dst_node_type=edge.dst_node_type,
                dst_qualified_name=edge.dst_qualified_name,
                edge_type=edge.edge_type,
                confidence=edge.confidence,
            )
            for edge in sorted(
                edges,
                key=lambda edge: (
                    edge.src_qualified_name,
                    edge.dst_qualified_name,
                    edge.edge_type,
                ),
            )
        ],
        call_records=[
            CallRecord(
                qualified_name=call.qualified_name,
                node_type=call.node_type,
                callee_identifiers=list(call.callee_identifiers),
            )
            for call in calls
        ],
        diagnostics=dict(diagnostics),
    )


__all__ = ["build_analysis_result"]
