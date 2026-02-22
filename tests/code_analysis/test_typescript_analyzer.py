# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.languages.typescript import TypeScriptAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


def test_typescript_analyzer_extracts_structure(tmp_path):
    module = """
    import { helper } from './utils.js';
    export class Foo {
      bar() {
        helper();
      }
    }
    export function outer() {
      const inner = () => helper();
      inner();
    }
    export function helper() {}
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/mod.ts"),
        language="typescript",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    node_types = {node.node_type for node in result.nodes}
    assert {"module", "class", "function", "method"}.issubset(node_types)
    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    assert not import_edges
    assert not [edge for edge in result.edges if edge.edge_type == "CALLS"]
    method_edges = [edge for edge in result.edges if edge.edge_type == "DEFINES_METHOD"]
    assert method_edges and method_edges[0].src_node_type == "class"
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    outer_name = f"{module_name}.outer"
    helper_name = f"{module_name}.helper"
    assert outer_name in call_records
    assert helper_name in call_records[outer_name]


def test_typescript_nested_function_declaration_is_not_structural(tmp_path):
    module = """
    export function outer() {
      function inner() {
        helper();
      }
      inner();
    }
    export function helper() {}
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/mod.ts"),
        language="typescript",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    function_nodes = {
        node.qualified_name for node in result.nodes if node.node_type == "function"
    }
    assert f"{module_name}.outer" in function_nodes
    assert f"{module_name}.helper" in function_nodes
    assert f"{module_name}.inner" not in function_nodes

    call_records = {record.qualified_name for record in result.call_records}
    assert f"{module_name}.inner" not in call_records


def test_typescript_analyzer_collects_internal_imports_and_reexports(tmp_path):
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    (src / "utils.ts").write_text("export function helper() {}", encoding="utf-8")
    module = """
    import { helper } from './utils';
    export { helper as helperAlias } from './utils';
    export function run() {
      helper();
    }
    """
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/mod.ts"),
        language="typescript",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    utils_record = FileRecord(
        path=src / "utils.ts",
        relative_path=Path("src/utils.ts"),
        language="typescript",
    )
    utils_snapshot = FileSnapshot(
        record=utils_record,
        file_id="file2",
        blob_sha="hash2",
        size=1,
        line_count=1,
        content=b" ",
    )
    utils_module = analyzer.module_name(repo, utils_snapshot)
    analyzer.module_index = {module_name, utils_module}
    result = analyzer.analyze(snapshot, module_name)
    import_targets = {
        edge.dst_qualified_name
        for edge in result.edges
        if edge.edge_type == "IMPORTS_DECLARED"
    }
    assert utils_module in import_targets


def test_typescript_analyzer_resolves_this_field_constructor_assignments(tmp_path):
    module = """
    class Service {
      run() {}
    }
    export class Controller {
      constructor() {
        this.svc = new Service();
      }
      handle() {
        this.svc.run();
      }
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/mod.ts"),
        language="typescript",
    )
    snapshot = FileSnapshot(
        record=record,
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    assert f"{module_name}.Service.run" in call_records[f"{module_name}.Controller.handle"]
