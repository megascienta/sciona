# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pytest

from sciona.code_analysis.core.normalize.model import AnalysisResult, EdgeRecord, SemanticNodeRecord
from sciona.code_analysis.core.structural_assembler import StructuralAssembler


class _DummyConn:
    pass


class _DummyStore:
    pass


def _node(
    *,
    node_type: str,
    qname: str,
    start: int | None,
    end: int | None,
) -> SemanticNodeRecord:
    return SemanticNodeRecord(
        language="python",
        node_type=node_type,
        qualified_name=qname,
        display_name=qname.rsplit(".", 1)[-1],
        file_path=Path("pkg/mod.py"),
        start_line=1,
        end_line=1,
        start_byte=start,
        end_byte=end,
    )


def test_lexical_contains_rejects_multiple_parents() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            _node(node_type="module", qname="pkg.mod", start=0, end=100),
            _node(node_type="type", qname="pkg.mod.A", start=10, end=80),
            _node(node_type="type", qname="pkg.mod.B", start=20, end=90),
            _node(node_type="callable", qname="pkg.mod.A.fn", start=30, end=40),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="type",
                src_qualified_name="pkg.mod.A",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.A.fn",
                edge_type="LEXICALLY_CONTAINS",
            ),
            EdgeRecord(
                src_language="python",
                src_node_type="type",
                src_qualified_name="pkg.mod.B",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.A.fn",
                edge_type="LEXICALLY_CONTAINS",
            ),
        ],
        call_records=[],
    )
    with pytest.raises(ValueError, match="multiple lexical parents"):
        assembler._validate_lexical_containment(analysis)


def test_lexical_contains_rejects_identical_parent_child_span() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            _node(node_type="module", qname="pkg.mod", start=0, end=100),
            _node(node_type="callable", qname="pkg.mod.fn", start=0, end=100),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.fn",
                edge_type="LEXICALLY_CONTAINS",
            )
        ],
        call_records=[],
    )
    with pytest.raises(ValueError, match="does not enclose"):
        assembler._validate_lexical_containment(analysis)


def test_lexical_contains_allows_equal_start_boundary_when_not_identical() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            _node(node_type="module", qname="pkg.mod", start=0, end=100),
            _node(node_type="callable", qname="pkg.mod.fn", start=0, end=90),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.fn",
                edge_type="LEXICALLY_CONTAINS",
            )
        ],
        call_records=[],
    )
    assembler._validate_lexical_containment(analysis)


def test_lexical_contains_allows_equal_end_boundary_when_not_identical() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            _node(node_type="module", qname="pkg.mod", start=0, end=100),
            _node(node_type="callable", qname="pkg.mod.fn", start=10, end=100),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.fn",
                edge_type="LEXICALLY_CONTAINS",
            )
        ],
        call_records=[],
    )
    assembler._validate_lexical_containment(analysis)


def test_lexical_contains_allows_parent_and_last_child_same_end_byte() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            _node(node_type="module", qname="pkg.mod", start=0, end=200),
            _node(node_type="type", qname="pkg.mod.A", start=10, end=180),
            _node(node_type="callable", qname="pkg.mod.A.last", start=120, end=180),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.mod",
                dst_language="python",
                dst_node_type="type",
                dst_qualified_name="pkg.mod.A",
                edge_type="LEXICALLY_CONTAINS",
            ),
            EdgeRecord(
                src_language="python",
                src_node_type="type",
                src_qualified_name="pkg.mod.A",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.A.last",
                edge_type="LEXICALLY_CONTAINS",
            ),
        ],
        call_records=[],
    )
    assembler._validate_lexical_containment(analysis)


def test_lexical_contains_rejects_cycles() -> None:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    analysis = AnalysisResult(
        nodes=[
            _node(node_type="module", qname="pkg.mod", start=0, end=100),
            _node(node_type="callable", qname="pkg.mod.a", start=None, end=None),
            _node(node_type="callable", qname="pkg.mod.b", start=None, end=None),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="callable",
                src_qualified_name="pkg.mod.a",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.b",
                edge_type="LEXICALLY_CONTAINS",
            ),
            EdgeRecord(
                src_language="python",
                src_node_type="callable",
                src_qualified_name="pkg.mod.b",
                dst_language="python",
                dst_node_type="callable",
                dst_qualified_name="pkg.mod.a",
                edge_type="LEXICALLY_CONTAINS",
            ),
        ],
        call_records=[],
    )
    with pytest.raises(ValueError, match="cycle"):
        assembler._validate_lexical_containment(analysis)
