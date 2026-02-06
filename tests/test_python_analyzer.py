# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.languages.python import PythonAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


def test_python_analyzer_extracts_structure(tmp_path):
    module = """
from .helpers import helper as helper_alias
from . import local_helper
import pkg.utils

class Foo:
    def bar(self):
        helper()

def helper():
    pass
"""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    file_path = pkg / "mod.py"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = PythonAnalyzer()
    result = analyzer.analyze(snapshot, "pkg.mod")
    node_types = {node.node_type for node in result.nodes}
    assert {"module", "class", "method", "function"}.issubset(node_types)
    assert not [edge for edge in result.edges if edge.edge_type == "CALLS"]
    method_edges = [edge for edge in result.edges if edge.edge_type == "DEFINES_METHOD"]
    assert method_edges and method_edges[0].src_node_type == "class"
    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    imported = {edge.dst_qualified_name for edge in import_edges}
    assert {"pkg.helpers", "pkg.utils", "pkg"}.issubset(imported)
