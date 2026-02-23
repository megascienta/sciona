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
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    node_types = {node.node_type for node in result.nodes}
    assert {"module", "class", "method"}.issubset(node_types)

    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    assert not import_edges

    module_node = next(node for node in result.nodes if node.node_type == "module")
    assert (
        module_node.metadata
        and module_node.metadata.get("package") == "com.example.foo"
    )

    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    class_name = f"{module_name}.Foo"
    helper_key = f"{class_name}.helper"
    assert helper_key in call_records
    module_package = module_name.rsplit(".", 1)[0]
    assert {
        f"{module_name}.Baz.Baz",
        f"{class_name}.qux",
        f"{module_package}.Runnable.run",
    }.issubset(call_records[helper_key])
    method_nodes = {
        node.qualified_name for node in result.nodes if node.node_type == "method"
    }
    assert method_nodes == {
        f"{class_name}.Foo",
        f"{class_name}.helper",
        f"{class_name}.qux",
    }


def test_java_analyzer_nested_class_qname(tmp_path):
    module = """
    package com.example.foo;

    public class Outer {
        class Inner {
            void ping() {}
        }
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "Outer.java"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/Outer.java"),
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
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.Outer" in qnames
    assert f"{module_name}.Outer.Inner" in qnames
    assert f"{module_name}.Outer.Inner.ping" in qnames
