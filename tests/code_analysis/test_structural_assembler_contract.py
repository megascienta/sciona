# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.normalize.model import (
    AnalysisResult,
    EdgeRecord,
    FileRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from sciona.code_analysis.core.structural_assembler import StructuralAssembler


class _DummyConn:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("DB access is not expected in this test")


class _DummyStore:
    pass


def test_persist_analysis_sorts_edges_by_source_target_edge_type(monkeypatch) -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    captured: list[tuple[str, str, str]] = []

    def _fake_emit_structural_node(node, _snapshot_id):
        return f"id::{node.qualified_name}"

    def _fake_emit_node_instances(*_args, **_kwargs):
        return None

    def _fake_emit_edges(_snapshot_id, edges, _node_id_map):
        captured.extend(
            [
                (edge.src_qualified_name, edge.dst_qualified_name, edge.edge_type)
                for edge in edges
            ]
        )

    monkeypatch.setattr(assembler, "_emit_structural_node", _fake_emit_structural_node)
    monkeypatch.setattr(assembler, "_emit_node_instances", _fake_emit_node_instances)
    monkeypatch.setattr(assembler, "_emit_edges", _fake_emit_edges)

    nodes = [
        SemanticNodeRecord(
            language="python",
            node_type="function",
            qualified_name="pkg.mod.src",
            display_name="src",
            file_path=Path("pkg/mod.py"),
            start_line=1,
            end_line=1,
        ),
        SemanticNodeRecord(
            language="python",
            node_type="function",
            qualified_name="pkg.mod.a",
            display_name="a",
            file_path=Path("pkg/mod.py"),
            start_line=1,
            end_line=1,
        ),
        SemanticNodeRecord(
            language="python",
            node_type="function",
            qualified_name="pkg.mod.b",
            display_name="b",
            file_path=Path("pkg/mod.py"),
            start_line=1,
            end_line=1,
        ),
    ]
    edges = [
        EdgeRecord(
            src_language="python",
            src_node_type="function",
            src_qualified_name="pkg.mod.src",
            dst_language="python",
            dst_node_type="function",
            dst_qualified_name="pkg.mod.b",
            edge_type="CONTAINS",
        ),
        EdgeRecord(
            src_language="python",
            src_node_type="function",
            src_qualified_name="pkg.mod.src",
            dst_language="python",
            dst_node_type="function",
            dst_qualified_name="pkg.mod.a",
            edge_type="ZZZ",
        ),
        EdgeRecord(
            src_language="python",
            src_node_type="function",
            src_qualified_name="pkg.mod.src",
            dst_language="python",
            dst_node_type="function",
            dst_qualified_name="pkg.mod.a",
            edge_type="AAA",
        ),
    ]
    snapshot = FileSnapshot(
        record=FileRecord(
            path=Path("pkg/mod.py"),
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="f1",
        blob_sha="deadbeef",
        size=0,
        line_count=1,
        content=b"",
    )

    assembler.persist_analysis(
        snapshot_id="s1",
        analysis=AnalysisResult(nodes=nodes, edges=edges, call_records=[]),
        file_snapshot=snapshot,
    )

    assert captured == [
        ("pkg.mod.src", "pkg.mod.a", "AAA"),
        ("pkg.mod.src", "pkg.mod.a", "ZZZ"),
        ("pkg.mod.src", "pkg.mod.b", "CONTAINS"),
    ]
