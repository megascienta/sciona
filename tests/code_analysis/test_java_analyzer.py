# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.languages.java import JavaAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


def test_java_analyzer_extracts_structure_and_calls(tmp_path):
    module = """
    package com.example.foo;
    import java.util.List;
    import static java.util.Collections.emptyList;

    public class Foo {
        public Foo() {
            this.helper();
        }

        public void helper() {
            baz();
            new Baz();
            Runnable r = () -> qux();
            r.run();
        }

        public void qux() {}
    }

    class Baz {}
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "Foo.java"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/Foo.java"),
        language="java",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = JavaAnalyzer()
    result = analyzer.analyze(snapshot, "src.Foo")

    node_types = {node.node_type for node in result.nodes}
    assert {"module", "class", "method"}.issubset(node_types)

    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    imported = {edge.dst_qualified_name for edge in import_edges}
    assert "java.util.List" in imported
    assert "java.util.Collections" in imported

    module_node = next(node for node in result.nodes if node.node_type == "module")
    assert (
        module_node.metadata
        and module_node.metadata.get("package") == "com.example.foo"
    )

    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    assert "src.Foo.Foo.helper" in call_records
    assert {"baz", "Baz", "src.Foo.Foo.qux"}.issubset(
        call_records["src.Foo.Foo.helper"]
    )
