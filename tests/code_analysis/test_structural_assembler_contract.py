# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.core.normalize_model import (
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


class _RecordingStore:
    def __init__(self) -> None:
        self.edges: list[tuple[str, str, str]] = []

    def insert_edge(self, _conn, **kwargs) -> None:
        self.edges.append(
            (
                kwargs["src_structural_id"],
                kwargs["dst_structural_id"],
                kwargs["edge_type"],
            )
        )


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


def test_persist_analysis_sorts_nodes_by_file_path_then_qualified_name(monkeypatch) -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    captured: list[str] = []

    def _fake_emit_structural_node(node, _snapshot_id):
        captured.append(node.qualified_name)
        return f"id::{node.qualified_name}"

    monkeypatch.setattr(assembler, "_emit_structural_node", _fake_emit_structural_node)
    monkeypatch.setattr(assembler, "_emit_node_instances", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(assembler, "_emit_edges", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(assembler, "_validate_lexical_containment", lambda _analysis: None)

    nodes = [
        SemanticNodeRecord(
            language="python",
            node_type="callable",
            qualified_name="pkg.zeta.run",
            display_name="run",
            file_path=Path("pkg/zeta.py"),
            start_line=1,
            end_line=1,
        ),
        SemanticNodeRecord(
            language="python",
            node_type="callable",
            qualified_name="pkg.alpha.run",
            display_name="run",
            file_path=Path("pkg/alpha.py"),
            start_line=1,
            end_line=1,
        ),
        SemanticNodeRecord(
            language="python",
            node_type="module",
            qualified_name="pkg.alpha",
            display_name="alpha",
            file_path=Path("pkg/alpha.py"),
            start_line=1,
            end_line=1,
        ),
    ]
    snapshot = FileSnapshot(
        record=FileRecord(
            path=Path("pkg/alpha.py"),
            relative_path=Path("pkg/alpha.py"),
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
        analysis=AnalysisResult(nodes=nodes, edges=[], call_records=[]),
        file_snapshot=snapshot,
    )

    assert captured == [
        "pkg.alpha",
        "pkg.alpha.run",
        "pkg.zeta.run",
    ]


def test_normalize_call_records_preserves_observed_unindexed_dotted_identifier() -> None:
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


def test_persist_analysis_counts_unresolved_edges(monkeypatch) -> None:
    assembler = StructuralAssembler(_DummyConn(), _RecordingStore())
    assembler.structural_cache = {
        ("python", "module", "pkg.other"): "module::other",
    }
    monkeypatch.setattr(
        assembler, "_emit_structural_node", lambda node, _snapshot_id: f"id::{node.qualified_name}"
    )
    monkeypatch.setattr(assembler, "_emit_node_instances", lambda *_args, **_kwargs: None)
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
    analysis = AnalysisResult(
        nodes=[
            SemanticNodeRecord(
                language="python",
                node_type="module",
                qualified_name="pkg.mod",
                display_name="mod",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=3,
                start_byte=0,
                end_byte=10,
            ),
            SemanticNodeRecord(
                language="python",
                node_type="callable",
                qualified_name="pkg.mod.run",
                display_name="run",
                file_path=Path("pkg/mod.py"),
                start_line=1,
                end_line=2,
                start_byte=1,
                end_byte=5,
            ),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.run",
                edge_type="LEXICALLY_CONTAINS",
            ),
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="module",
                dst_qualified_name="pkg.other",
                edge_type="IMPORTS_DECLARED",
            ),
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="module",
                dst_qualified_name="pkg.missing",
                edge_type="IMPORTS_DECLARED",
            ),
        ],
        call_records=[],
    )

    assembler.persist_analysis("s1", analysis, snapshot)

    assert assembler.emission_diagnostics == {
        "unresolved_edges_total": 1,
        "unresolved_edges_by_type": {"IMPORTS_DECLARED": 1},
    }


def test_normalize_call_records_preserves_observed_terminal_without_provenance() -> None:
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

    assert [record.callee_identifiers for record in normalized.call_records] == [["run"]]
    assert assembler.call_gate_diagnostics == {}


def test_normalize_call_records_preserves_observed_module_scoped_terminal() -> None:
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
    assert normalized.call_records[0].callee_identifiers == ["run"]
    assert assembler.call_gate_diagnostics == {}
