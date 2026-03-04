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
    assert {"module", "type", "callable"}.issubset(node_types)
    import_edges = [
        edge for edge in result.edges if edge.edge_type == "IMPORTS_DECLARED"
    ]
    assert not import_edges
    assert not [edge for edge in result.edges if edge.edge_type == "CALLS"]
    method_edges = [edge for edge in result.edges if edge.edge_type == "LEXICALLY_CONTAINS"]
    assert method_edges
    call_records = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    outer_name = f"{module_name}.outer.inner"
    helper_name = f"{module_name}.helper"
    assert outer_name in call_records
    assert helper_name in call_records[outer_name]




def test_typescript_nested_function_declaration_is_structural(tmp_path):
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
        node.qualified_name for node in result.nodes if node.node_type == "callable"
    }
    assert f"{module_name}.outer" in function_nodes
    assert f"{module_name}.helper" in function_nodes
    assert f"{module_name}.outer.inner" in function_nodes

    call_records = {record.qualified_name for record in result.call_records}
    assert f"{module_name}.outer.inner" in call_records
    by_caller = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    assert f"{module_name}.helper" in by_caller[f"{module_name}.outer.inner"]


def test_typescript_nested_arrow_and_function_expression_are_structural_when_bound(tmp_path):
    module = """
    export function outer() {
      const innerArrow = () => 1;
      const innerExpr = function() { return 2; };
      return innerArrow() + innerExpr();
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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
        node.qualified_name for node in result.nodes if node.node_type == "callable"
    }
    assert f"{module_name}.outer" in function_nodes
    assert f"{module_name}.outer.innerArrow" in function_nodes
    assert f"{module_name}.outer.innerExpr" in function_nodes
    callers = {record.qualified_name for record in result.call_records}
    assert f"{module_name}.outer.innerArrow" not in callers
    assert f"{module_name}.outer.innerExpr" not in callers


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
def test_typescript_analyzer_collects_import_equals_declaration(tmp_path):
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    (src / "utils.ts").write_text("export const helper = () => 1;", encoding="utf-8")
    module = """
    import utilsAlias = require('./utils');
    export function run() {
      return utilsAlias.helper();
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


def test_typescript_analyzer_collects_dynamic_import_literal(tmp_path):
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    (src / "utils.ts").write_text("export const helper = () => 1;", encoding="utf-8")
    module = """
    export async function run() {
      const mod = await import(`./utils`);
      return mod.helper();
    }
    """
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    utils_snapshot = FileSnapshot(
        record=FileRecord(
            path=src / "utils.ts",
            relative_path=Path("src/utils.ts"),
            language="typescript",
        ),
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


def test_typescript_analyzer_ignores_dynamic_import_template_with_substitution(tmp_path):
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    (src / "utils.ts").write_text("export const helper = () => 1;", encoding="utf-8")
    module = """
    const name = "utils";
    export async function run() {
      const mod = await import(`./${name}`);
      return mod.helper();
    }
    """
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
        file_id="file",
        blob_sha="hash",
        size=len(module.encode("utf-8")),
        line_count=module.count("\n"),
        content=module.encode("utf-8"),
    )
    analyzer = TypeScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    utils_snapshot = FileSnapshot(
        record=FileRecord(
            path=src / "utils.ts",
            relative_path=Path("src/utils.ts"),
            language="typescript",
        ),
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
    assert utils_module not in import_targets


def test_typescript_analyzer_does_not_emit_decorator_structural_entities(tmp_path):
    module = """
    function sealed(target: object) { return target; }
    function logged(target: object, key: string, descriptor: PropertyDescriptor) { return descriptor; }
    @sealed
    export class Service {
      @logged
      run() {}
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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
    assert not [node for node in result.nodes if node.node_type == "decorator"]
    assert not [edge for edge in result.edges if edge.edge_type == "DECORATED_BY"]


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


def test_typescript_analyzer_nested_and_class_expression_qnames(tmp_path):
    module = """
    export class Outer {
      static Inner = class {
        ping() {}
      }
      method() {}
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
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.Outer" in qnames
    assert f"{module_name}.Outer.method" in qnames


def test_typescript_analyzer_resolves_module_alias_assignments(tmp_path):
    module = """
    class Service {
      run() {}
    }
    const a = new Service();
    const b = a;
    export function use() {
      b.run();
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
    assert f"{module_name}.Service.run" in call_records[f"{module_name}.use"]


def test_typescript_module_name_strips_d_ts_suffix(tmp_path):
    module = "export const value = 1;\n"
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "types.d.ts"
    file_path.write_text(module, encoding="utf-8")
    record = FileRecord(
        path=file_path,
        relative_path=Path("src/types.d.ts"),
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
    assert analyzer.module_name(repo, snapshot) == f"{repo.name}.src.types"


def test_typescript_analyzer_does_not_bleed_calls_from_nested_class_expression(tmp_path):
    module = """
    export function helper() {}
    export class Controller {
      handle() {
        const Local = class {
          run() { helper(); }
        };
        const l = new Local();
        l.run();
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
    handle_calls = call_records.get(f"{module_name}.Controller.handle", set())
    assert f"{module_name}.helper" not in handle_calls


def test_typescript_analyzer_extracts_abstract_class_and_interface(tmp_path):
    module = """
    export abstract class Service {
      abstract process(): void;
    }
    export interface Repo {
      find(): User;
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
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.Service" in qnames
    assert f"{module_name}.Service.process" in qnames
    assert f"{module_name}.Repo" in qnames
    assert f"{module_name}.Repo.find" in qnames


def test_typescript_analyzer_resolves_typed_constructor_parameter_field(tmp_path):
    module = """
    class UserSvc {
      run() {}
    }
    export class Controller {
      constructor(private readonly svc: UserSvc) {}
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
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.UserSvc.run" in call_records[f"{module_name}.Controller.handle"]


def test_typescript_analyzer_resolves_typed_field_without_initializer(tmp_path):
    module = """
    class UserSvc {
      run() {}
    }
    export class Controller {
      private svc: UserSvc;
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
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.UserSvc.run" in call_records[f"{module_name}.Controller.handle"]


def test_typescript_analyzer_resolves_generic_typed_constructor_parameter_field(tmp_path):
    module = """
    class UserSvc {
      run() {}
    }
    export class Controller {
      constructor(private readonly svc: Partial<UserSvc>) {}
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
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.UserSvc.run" in call_records[f"{module_name}.Controller.handle"]


def test_typescript_analyzer_keeps_method_in_class_declared_inside_function(tmp_path):
    module = """
    export function outer() {
      class Inner {
        run() {
          helper();
        }
      }
      return new Inner();
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
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.outer.Inner" in qnames
    assert f"{module_name}.outer.Inner.run" in qnames
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.helper" in call_records[f"{module_name}.outer.Inner.run"]


def test_typescript_analyzer_disambiguates_duplicate_local_class_names(tmp_path):
    module = """
    describe('suite', () => {
      it('case-a', () => {
        class TestClass {
          alpha() {}
        }
      });
      it('case-b', () => {
        class TestClass {
          beta() {}
        }
      });
    });
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
    first = analyzer.analyze(snapshot, module_name)
    second = analyzer.analyze(snapshot, module_name)
    assert [node.qualified_name for node in first.nodes] == [
        node.qualified_name for node in second.nodes
    ]
    result = first
    qnames = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.TestClass" in qnames
    assert f"{module_name}.TestClass-2" in qnames
    assert f"{module_name}.TestClass.alpha" in qnames
    assert f"{module_name}.TestClass-2.beta" in qnames
    test_class_nodes = [
        node
        for node in result.nodes
        if node.node_type == "type" and node.qualified_name.startswith(f"{module_name}.TestClass")
    ]
    assert {node.display_name for node in test_class_nodes} == {"TestClass"}


def test_typescript_analyzer_emits_kind_metadata_for_interface_and_signatures(tmp_path):
    module = """
    export class Base {}
    export interface IWorker {
      execute(): void;
    }
    @sealed
    export class Worker extends Base {
      execute() {}
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
    interface_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.IWorker"
    )
    assert (interface_node.metadata or {}).get("kind") == "interface"
    signature_node = next(
        node
        for node in result.nodes
        if node.qualified_name == f"{module_name}.IWorker.execute"
    )
    assert (signature_node.metadata or {}).get("signature_only") is True
    worker_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.Worker"
    )
    assert isinstance((worker_node.metadata or {}).get("bases"), list)


def test_typescript_analyzer_emits_function_and_async_metadata(tmp_path):
    module = """
    export async function load() {}
    const worker = async function () {};
    export class Service {
      async run() {}
      task = async () => {};
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

    load_node = next(node for node in result.nodes if node.qualified_name == f"{module_name}.load")
    worker_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.worker"
    )
    run_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.Service.run"
    )
    task_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.Service.task"
    )

    assert (load_node.metadata or {}).get("kind") == "async_callable"
    assert (worker_node.metadata or {}).get("kind") == "async_callable"
    assert (run_node.metadata or {}).get("kind") == "async_callable"
    assert (task_node.metadata or {}).get("kind") == "async_callable"


def test_typescript_analyzer_emits_class_expression_bases_metadata(tmp_path):
    module = """
    class Base {}
    const Derived = class extends Base {
      run() {}
    };
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

    derived_node = next(
        node for node in result.nodes if node.qualified_name == f"{module_name}.Derived"
    )
    assert "Base" in ((derived_node.metadata or {}).get("bases") or [])


def test_typescript_analyzer_resolves_typed_method_parameter_receiver(tmp_path):
    module = """
    class Module {
      run() {}
    }
    export class Controller {
      handle(mod: Module) {
        mod.run();
      }
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.Module.run" in call_records[f"{module_name}.Controller.handle"]


def test_typescript_analyzer_resolves_typed_local_declaration_receiver(tmp_path):
    module = """
    class ServerGrpc {
      start() {}
    }
    export function boot() {
      let server: ServerGrpc;
      server.start();
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.ServerGrpc.start" in call_records[f"{module_name}.boot"]


def test_typescript_analyzer_promotes_bound_object_literal_methods(tmp_path):
    module = """
    export function helper() {}
    export function outer() {
      const tools = {
        run() { helper(); },
        ping: () => helper(),
        pong: function() { helper(); },
      };
      return tools;
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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

    qnames = {node.qualified_name for node in result.nodes if node.node_type == "callable"}
    assert f"{module_name}.outer.tools.run" in qnames
    assert f"{module_name}.outer.tools.ping" in qnames
    assert f"{module_name}.outer.tools.pong" in qnames
    role_by_qname = {
        node.qualified_name: (node.metadata or {}).get("callable_role")
        for node in result.nodes
        if node.node_type == "callable"
    }
    assert role_by_qname[f"{module_name}.outer.tools.run"] == "bound"
    assert role_by_qname[f"{module_name}.outer.tools.ping"] == "bound"
    assert role_by_qname[f"{module_name}.outer.tools.pong"] == "bound"

    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.helper" in call_records[f"{module_name}.outer.tools.run"]
    assert f"{module_name}.helper" in call_records[f"{module_name}.outer.tools.ping"]
    assert f"{module_name}.helper" in call_records[f"{module_name}.outer.tools.pong"]


def test_typescript_analyzer_promotes_anonymous_export_default_callable(tmp_path):
    module = """
    export function helper() {}
    export default function() {
      helper();
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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

    default_node = next(
        node for node in result.nodes if node.node_type == "callable" and node.qualified_name == f"{module_name}.default"
    )
    assert (default_node.metadata or {}).get("callable_role") == "bound"
    call_records = {
        rec.qualified_name: set(rec.callee_identifiers) for rec in result.call_records
    }
    assert f"{module_name}.helper" in call_records[f"{module_name}.default"]


def test_typescript_callable_roles_cover_declared_nested_bound_constructor(tmp_path):
    module = """
    class Service {
      constructor() {}
      run() {}
    }
    export function outer() {
      function inner() {}
      const bound = () => 1;
      return bound() + inner();
    }
    """
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.ts"
    file_path.write_text(module, encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.ts"),
            language="typescript",
        ),
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

    role_by_qname = {
        node.qualified_name: (node.metadata or {}).get("callable_role")
        for node in result.nodes
        if node.node_type == "callable"
    }
    assert role_by_qname[f"{module_name}.Service.constructor"] == "constructor"
    assert role_by_qname[f"{module_name}.Service.run"] == "declared"
    assert role_by_qname[f"{module_name}.outer"] == "declared"
    assert role_by_qname[f"{module_name}.outer.inner"] == "nested"
    assert role_by_qname[f"{module_name}.outer.bound"] == "bound"
