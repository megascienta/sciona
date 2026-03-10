# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Lightweight structural extraction buffer used as adapter/core seam."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Iterable, Iterator, TypeVar

from ...normalize_model import AnalysisResult, CallRecord, EdgeRecord, SemanticNodeRecord
from .ir_builder import build_analysis_result
from .structural_ir import IRCall, IREdge, IRNode

TModel = TypeVar("TModel")
TIR = TypeVar("TIR")


class _TransformList(Generic[TModel, TIR]):
    """List-like adapter that stores IR while accepting model records."""

    def __init__(self, convert):
        self._convert = convert
        self._items: list[TIR] = []

    def append(self, item: TModel | TIR) -> None:
        self._items.append(self._convert(item))

    def extend(self, items: Iterable[TModel | TIR]) -> None:
        for item in items:
            self.append(item)

    def __iter__(self) -> Iterator[TIR]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index):
        return self._items[index]

    def as_list(self) -> list[TIR]:
        return list(self._items)


@dataclass
class ExtractionBuffer:
    """Mutable collection of extraction outputs with deterministic finalization."""

    nodes: _TransformList[SemanticNodeRecord, IRNode] = field(
        default_factory=lambda: _TransformList(
            lambda node: node if isinstance(node, IRNode) else IRNode.from_record(node)
        )
    )
    edges: _TransformList[EdgeRecord, IREdge] = field(
        default_factory=lambda: _TransformList(
            lambda edge: edge if isinstance(edge, IREdge) else IREdge.from_record(edge)
        )
    )
    call_records: _TransformList[CallRecord, IRCall] = field(
        default_factory=lambda: _TransformList(
            lambda call: call if isinstance(call, IRCall) else IRCall.from_record(call)
        )
    )
    diagnostics: dict[str, object] = field(default_factory=dict)

    def add_node(self, node: SemanticNodeRecord) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: EdgeRecord) -> None:
        self.edges.append(edge)

    def add_call(self, call: CallRecord) -> None:
        self.call_records.append(call)

    def finalize(self) -> AnalysisResult:
        return build_analysis_result(
            nodes=self.nodes.as_list(),
            edges=self.edges.as_list(),
            calls=self.call_records.as_list(),
            diagnostics=dict(self.diagnostics),
        )


__all__ = ["ExtractionBuffer"]
