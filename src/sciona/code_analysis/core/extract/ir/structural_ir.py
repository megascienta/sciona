# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Minimal structural IR records emitted by language adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...normalize_model import CallRecord, EdgeRecord, SemanticNodeRecord


@dataclass
class IRNode:
    language: str
    node_type: str
    qualified_name: str
    display_name: str
    file_path: Path
    start_line: int
    end_line: int
    start_byte: int | None = None
    end_byte: int | None = None
    file_id: str | None = None
    metadata: dict[str, object] | None = None

    @classmethod
    def from_record(cls, node: SemanticNodeRecord) -> "IRNode":
        return cls(
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


@dataclass
class IREdge:
    src_language: str
    src_node_type: str
    src_qualified_name: str
    dst_language: str
    dst_node_type: str
    dst_qualified_name: str
    edge_type: str
    confidence: float = 1.0

    @classmethod
    def from_record(cls, edge: EdgeRecord) -> "IREdge":
        return cls(
            src_language=edge.src_language,
            src_node_type=edge.src_node_type,
            src_qualified_name=edge.src_qualified_name,
            dst_language=edge.dst_language,
            dst_node_type=edge.dst_node_type,
            dst_qualified_name=edge.dst_qualified_name,
            edge_type=edge.edge_type,
            confidence=edge.confidence,
        )


@dataclass
class IRCall:
    qualified_name: str
    node_type: str
    callee_identifiers: list[str]

    @classmethod
    def from_record(cls, call: CallRecord) -> "IRCall":
        return cls(
            qualified_name=call.qualified_name,
            node_type=call.node_type,
            callee_identifiers=list(call.callee_identifiers),
        )


__all__ = ["IRCall", "IREdge", "IRNode"]
