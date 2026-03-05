# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.ir.extraction_buffer import ExtractionBuffer
from sciona.code_analysis.core.normalize.model import (
    CallRecord,
    EdgeRecord,
    SemanticNodeRecord,
)


def test_extraction_buffer_finalize_sorts_edges() -> None:
    buffer = ExtractionBuffer()
    buffer.add_node(
        SemanticNodeRecord(
            language="python",
            node_type="module",
            qualified_name="pkg.mod",
            display_name="mod",
            file_path=Path("pkg/mod.py"),
            start_line=1,
            end_line=1,
        )
    )
    buffer.add_edge(
        EdgeRecord(
            src_language="python",
            src_node_type="module",
            src_qualified_name="pkg.mod",
            dst_language="python",
            dst_node_type="module",
            dst_qualified_name="pkg.z",
            edge_type="Z",
        )
    )
    buffer.add_edge(
        EdgeRecord(
            src_language="python",
            src_node_type="module",
            src_qualified_name="pkg.mod",
            dst_language="python",
            dst_node_type="module",
            dst_qualified_name="pkg.a",
            edge_type="A",
        )
    )
    buffer.add_call(
        CallRecord(
            qualified_name="pkg.mod.entry",
            node_type="callable",
            callee_identifiers=["pkg.other.f"],
        )
    )

    result = buffer.finalize()

    assert [edge.dst_qualified_name for edge in result.edges] == ["pkg.a", "pkg.z"]
    assert result.call_records[0].qualified_name == "pkg.mod.entry"


def test_extraction_buffer_finalize_copies_diagnostics() -> None:
    buffer = ExtractionBuffer()
    buffer.diagnostics["imports_seen"] = 2

    result = buffer.finalize()

    assert result.diagnostics == {"imports_seen": 2}
