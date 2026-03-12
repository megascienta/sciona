# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.languages.builtin.java import JavaAnalyzer
from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer
from sciona.code_analysis.languages.builtin.python import PythonAnalyzer
from sciona.code_analysis.languages.builtin.typescript import TypeScriptAnalyzer
from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot


def _snapshot(path: Path, rel: str, language: str, content: str) -> FileSnapshot:
    return FileSnapshot(
        record=FileRecord(path=path, relative_path=Path(rel), language=language),
        file_id="file",
        blob_sha="hash",
        size=len(content.encode("utf-8")),
        line_count=content.count("\n"),
        content=content.encode("utf-8"),
    )


def _call_map(result) -> dict[str, tuple[str, ...]]:
    return {
        record.qualified_name: tuple(record.callee_identifiers)
        for record in result.call_records
    }


def test_python_resolution_is_stable_across_runs(tmp_path):
    source = """
class Service:
    def run(self):
        pass
class Controller:
    def __init__(self):
        self.svc = Service()
    def handle(self):
        self.svc.run()
"""
    file_path = tmp_path / "pkg" / "mod.py"
    file_path.parent.mkdir()
    file_path.write_text(source, encoding="utf-8")
    analyzer = PythonAnalyzer()
    snapshot = _snapshot(file_path, "pkg/mod.py", "python", source)
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}

    run_1 = _call_map(analyzer.analyze(snapshot, module_name))
    run_2 = _call_map(analyzer.analyze(snapshot, module_name))
    assert run_1 == run_2


def test_typescript_resolution_is_stable_across_runs(tmp_path):
    source = """
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
    file_path = tmp_path / "src" / "mod.ts"
    file_path.parent.mkdir()
    file_path.write_text(source, encoding="utf-8")
    analyzer = TypeScriptAnalyzer()
    snapshot = _snapshot(file_path, "src/mod.ts", "typescript", source)
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}

    run_1 = _call_map(analyzer.analyze(snapshot, module_name))
    run_2 = _call_map(analyzer.analyze(snapshot, module_name))
    assert run_1 == run_2


def test_java_resolution_is_stable_across_runs(tmp_path):
    source = """
package com.example.foo;
public class Foo {
  void run() {}
  void call() {
    this.run();
  }
}
"""
    file_path = tmp_path / "src" / "Foo.java"
    file_path.parent.mkdir()
    file_path.write_text(source, encoding="utf-8")
    analyzer = JavaAnalyzer()
    snapshot = _snapshot(file_path, "src/Foo.java", "java", source)
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}

    run_1 = _call_map(analyzer.analyze(snapshot, module_name))
    run_2 = _call_map(analyzer.analyze(snapshot, module_name))
    assert run_1 == run_2


def test_java_resolution_recovers_constructor_parameter_assigned_field(tmp_path):
    source = """
package com.example.foo;
class Service {
  void run() {}
}
public class Foo {
  private final Service svc;
  Foo(Service svc) {
    this.svc = svc;
  }
  void call() {
    this.svc.run();
  }
}
"""
    file_path = tmp_path / "src" / "Foo.java"
    file_path.parent.mkdir()
    file_path.write_text(source, encoding="utf-8")
    analyzer = JavaAnalyzer()
    snapshot = _snapshot(file_path, "src/Foo.java", "java", source)
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}

    result = _call_map(analyzer.analyze(snapshot, module_name))
    assert f"{module_name}.Foo.call" in result
    assert f"{module_name}.Service.run" in result[f"{module_name}.Foo.call"]


def test_javascript_resolution_is_stable_across_runs(tmp_path):
    source = """
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
    file_path = tmp_path / "src" / "mod.js"
    file_path.parent.mkdir()
    file_path.write_text(source, encoding="utf-8")
    analyzer = JavaScriptAnalyzer()
    snapshot = _snapshot(file_path, "src/mod.js", "javascript", source)
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}

    run_1 = _call_map(analyzer.analyze(snapshot, module_name))
    run_2 = _call_map(analyzer.analyze(snapshot, module_name))
    assert run_1 == run_2
