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


def _node(*, node_type: str, qname: str, start: int, end: int) -> SemanticNodeRecord:
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
