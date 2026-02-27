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
    edge_types = {
        edge.edge_type
        for edge in result.edges
        if edge.src_qualified_name == f"{module_name}.Outer"
        and edge.dst_qualified_name == f"{module_name}.Outer.Inner"
    }
    assert {"CONTAINS", "NESTS"}.issubset(edge_types)


def test_java_analyzer_resolves_for_each_catch_and_instanceof_bindings(tmp_path):
    module = """
    class Item {
        void run() {}
    }

    class Err {
        void handle() {}
    }

    class Holder {
        void use(java.util.List<Item> items, Object obj) {
            for (Item item : items) {
                item.run();
            }
            try {
                throw new Err();
            } catch (Err e) {
                e.handle();
            }
            if (obj instanceof Item match) {
                match.run();
            }
        }
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "Holder.java"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/Holder.java"),
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
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    use_calls = call_records[f"{module_name}.Holder.use"]
    assert f"{module_name}.Item.run" in use_calls
    assert f"{module_name}.Err.handle" in use_calls


def test_java_analyzer_resolves_static_member_and_wildcard_imports(tmp_path):
    service_module = """
    package com.example;

    public class Service {
        public static void run() {}
        public static void execute() {}
    }
    """
    app_module = """
    package com.example;

    import static com.example.Service.run;
    import static com.example.Service.*;

    public class App {
        public void handle() {
            run();
            execute();
        }
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    service_path = src / "com" / "example" / "Service.java"
    service_path.parent.mkdir(parents=True)
    service_path.write_text(service_module, encoding="utf-8")
    app_path = src / "com" / "example" / "App.java"
    app_path.write_text(app_module, encoding="utf-8")

    analyzer = JavaAnalyzer()

    service_snapshot = FileSnapshot(
        record=FileRecord(
            path=service_path,
            relative_path=Path("src/com/example/Service.java"),
            language="java",
        ),
        file_id="service",
        blob_sha="hash",
        size=len(service_module.encode("utf-8")),
        line_count=service_module.count("\n"),
        content=service_module.encode("utf-8"),
    )
    app_snapshot = FileSnapshot(
        record=FileRecord(
            path=app_path,
            relative_path=Path("src/com/example/App.java"),
            language="java",
        ),
        file_id="app",
        blob_sha="hash",
        size=len(app_module.encode("utf-8")),
        line_count=app_module.count("\n"),
        content=app_module.encode("utf-8"),
    )

    service_module_name = analyzer.module_name(repo, service_snapshot)
    app_module_name = analyzer.module_name(repo, app_snapshot)
    analyzer.module_index = {service_module_name, app_module_name}

    # Prime class method map with Service first; App resolution reuses same analyzer instance.
    analyzer.analyze(service_snapshot, service_module_name)
    app_result = analyzer.analyze(app_snapshot, app_module_name)

    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in app_result.call_records
    }
    handle_calls = call_records[f"{app_module_name}.App.handle"]
    assert f"{service_module_name}.run" in handle_calls
    assert f"{service_module_name}.execute" in handle_calls

    module_node = next(node for node in app_result.nodes if node.node_type == "module")
    diagnostics = (module_node.metadata or {}).get("resolution_diagnostics")
    assert isinstance(diagnostics, dict)
    assert diagnostics.get("member_aliases", 0) >= 1
    assert diagnostics.get("static_wildcard_targets", 0) >= 1
    assert isinstance(diagnostics.get("call_resolution_outcomes"), dict)


def test_java_analyzer_emits_kind_metadata_for_class_like_and_methods(tmp_path):
    module = """
    @Entity
    interface Repo {
        void find();
    }
    class Service {
        Service() {}
        void run() {}
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "Mod.java"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/Mod.java"),
            language="java",
        ),
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
    interface_node = next(node for node in result.nodes if node.qualified_name.endswith(".Repo"))
    assert (interface_node.metadata or {}).get("kind") == "interface"
    ctor_node = next(node for node in result.nodes if node.qualified_name.endswith(".Service.Service"))
    assert (ctor_node.metadata or {}).get("kind") == "constructor"
    assert (ctor_node.metadata or {}).get("declared_in_kind") == "class"


def test_java_analyzer_resolves_constructor_new_assignment_on_this_field(tmp_path):
    module = """
    class Service {
        void run() {}
    }
    class Controller {
        Controller() {
            this.svc = new Service();
        }
        void handle() {
            this.svc.run();
        }
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "App.java"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/App.java"),
            language="java",
        ),
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
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    handle_calls = call_records[f"{module_name}.Controller.handle"]
    assert f"{module_name}.Service.run" in handle_calls


def test_java_analyzer_emits_local_implements_edges(tmp_path):
    module = """
    interface Repo {
        void find();
    }
    class Service implements Repo {
        public void find() {}
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "App.java"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/App.java"),
            language="java",
        ),
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
    edge_types = {
        edge.edge_type
        for edge in result.edges
        if edge.src_qualified_name == f"{module_name}.Service"
        and edge.dst_qualified_name == f"{module_name}.Repo"
    }
    assert "IMPLEMENTS" in edge_types
