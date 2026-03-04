# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.normalize.model import (
    AnalysisResult,
    CallRecord,
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
    monkeypatch.setattr(assembler, "_validate_lexical_containment", lambda _analysis: None)

    nodes = [
        SemanticNodeRecord(
            language="python",
            node_type="callable",
            qualified_name="pkg.mod.src",
            display_name="src",
            file_path=Path("pkg/mod.py"),
            start_line=1,
            end_line=1,
        ),
        SemanticNodeRecord(
            language="python",
            node_type="callable",
            qualified_name="pkg.mod.a",
            display_name="a",
            file_path=Path("pkg/mod.py"),
            start_line=1,
            end_line=1,
        ),
        SemanticNodeRecord(
            language="python",
            node_type="callable",
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
            src_node_type="callable",
            src_qualified_name="pkg.mod.src",
            dst_language="python",
            dst_node_type="callable",
            dst_qualified_name="pkg.mod.b",
            edge_type="LEXICALLY_CONTAINS",
        ),
        EdgeRecord(
            src_language="python",
            src_node_type="callable",
            src_qualified_name="pkg.mod.src",
            dst_language="python",
            dst_node_type="callable",
            dst_qualified_name="pkg.mod.a",
            edge_type="ZZZ",
        ),
        EdgeRecord(
            src_language="python",
            src_node_type="callable",
            src_qualified_name="pkg.mod.src",
            dst_language="python",
            dst_node_type="callable",
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
        ("pkg.mod.src", "pkg.mod.b", "LEXICALLY_CONTAINS"),
    ]


def test_normalize_call_records_strict_keeps_exact_qname() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            SemanticNodeRecord(
                language="python",
                node_type="module",
                qualified_name="pkg.mod",
                display_name="mod",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=10,
            ),
            SemanticNodeRecord(
                language="python",
                node_type="callable",
                qualified_name="pkg.mod.entry",
                display_name="entry",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=5,
            ),
        ],
        edges=[],
        call_records=[
            CallRecord(
                qualified_name="pkg.mod.entry",
                node_type="callable",
                callee_identifiers=["pkg.other.service.run"],
            )
        ],
    )
    snapshot = FileSnapshot(
        record=FileRecord(
            path=Path("pkg/mod.py"),
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="f1",
        blob_sha="hash",
        size=0,
        line_count=1,
        content=b"",
    )

    normalized = assembler._normalize_call_records(analysis, snapshot)

    assert len(normalized.call_records) == 1
    assert normalized.call_records[0].callee_identifiers == ["pkg.other.service.run"]


def test_normalize_call_records_strict_drops_terminal_without_provenance() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            SemanticNodeRecord(
                language="python",
                node_type="module",
                qualified_name="pkg.mod",
                display_name="mod",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=10,
            ),
            SemanticNodeRecord(
                language="python",
                node_type="callable",
                qualified_name="pkg.mod.entry",
                display_name="entry",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=5,
            ),
        ],
        edges=[],
        call_records=[
            CallRecord(
                qualified_name="pkg.mod.entry",
                node_type="callable",
                callee_identifiers=["run"],
            )
        ],
    )
    snapshot = FileSnapshot(
        record=FileRecord(
            path=Path("pkg/mod.py"),
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="f1",
        blob_sha="hash",
        size=0,
        line_count=1,
        content=b"",
    )

    normalized = assembler._normalize_call_records(analysis, snapshot)

    assert normalized.call_records == []
    diagnostics = assembler.call_gate_diagnostics
    assert diagnostics.get("identifiers_total") == 1
    assert diagnostics.get("accepted_identifiers") == 0
    assert diagnostics.get("dropped_identifiers") == 1
    assert diagnostics.get("dropped_by_resolver") == 1
    assert diagnostics.get("resolver_accepted_assembler_dropped") == 0
    dropped = diagnostics.get("dropped_by_reason") or {}
    assert dropped.get("no_candidates") == 1


def test_normalize_call_records_strict_accepts_module_scoped_terminal() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            SemanticNodeRecord(
                language="python",
                node_type="module",
                qualified_name="pkg.mod",
                display_name="mod",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=10,
            ),
            SemanticNodeRecord(
                language="python",
                node_type="callable",
                qualified_name="pkg.mod.entry",
                display_name="entry",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=5,
            ),
            SemanticNodeRecord(
                language="python",
                node_type="callable",
                qualified_name="pkg.mod.run",
                display_name="run",
                file_path=Path("pkg/mod.py"),
                start_line=6,
                end_line=8,
            ),
        ],
        edges=[],
        call_records=[
            CallRecord(
                qualified_name="pkg.mod.entry",
                node_type="callable",
                callee_identifiers=["run"],
            )
        ],
    )
    snapshot = FileSnapshot(
        record=FileRecord(
            path=Path("pkg/mod.py"),
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="f1",
        blob_sha="hash",
        size=0,
        line_count=1,
        content=b"",
    )

    normalized = assembler._normalize_call_records(analysis, snapshot)

    assert len(normalized.call_records) == 1
    assert normalized.call_records[0].callee_identifiers == ["pkg.mod.run"]
