# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Lightweight structural extraction buffer used as adapter/core seam."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..normalize.model import AnalysisResult, CallRecord, EdgeRecord, SemanticNodeRecord


@dataclass
class ExtractionBuffer:
    """Mutable collection of extraction outputs with deterministic finalization."""

    nodes: list[SemanticNodeRecord] = field(default_factory=list)
    edges: list[EdgeRecord] = field(default_factory=list)
    call_records: list[CallRecord] = field(default_factory=list)
    diagnostics: dict[str, object] = field(default_factory=dict)

    def add_node(self, node: SemanticNodeRecord) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: EdgeRecord) -> None:
        self.edges.append(edge)

    def add_call(self, call: CallRecord) -> None:
        self.call_records.append(call)

    def finalize(self) -> AnalysisResult:
        return AnalysisResult(
            nodes=list(self.nodes),
            edges=sorted(
                self.edges,
                key=lambda edge: (
                    edge.src_qualified_name,
                    edge.dst_qualified_name,
                    edge.edge_type,
                ),
            ),
            call_records=list(self.call_records),
            diagnostics=dict(self.diagnostics),
        )


__all__ = ["ExtractionBuffer"]
