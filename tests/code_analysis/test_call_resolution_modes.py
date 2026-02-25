# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.extract.languages.call_resolution_kernel import (
    CALL_RESOLUTION_MODE_ENV,
)
from sciona.code_analysis.core.extract.languages.java import JavaAnalyzer
from sciona.code_analysis.core.extract.languages.python import PythonAnalyzer
from sciona.code_analysis.core.extract.languages.typescript import TypeScriptAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


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


def test_python_resolution_modes_are_parity(tmp_path, monkeypatch):
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

    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "legacy")
    legacy = _call_map(analyzer.analyze(snapshot, module_name))
    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "shared")
    shared = _call_map(analyzer.analyze(snapshot, module_name))
    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "compare")
    compare = _call_map(analyzer.analyze(snapshot, module_name))

    assert shared == legacy
    assert compare == legacy


def test_typescript_resolution_modes_are_parity(tmp_path, monkeypatch):
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

    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "legacy")
    legacy = _call_map(analyzer.analyze(snapshot, module_name))
    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "shared")
    shared = _call_map(analyzer.analyze(snapshot, module_name))
    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "compare")
    compare = _call_map(analyzer.analyze(snapshot, module_name))

    assert shared == legacy
    assert compare == legacy


def test_java_resolution_modes_are_parity(tmp_path, monkeypatch):
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

    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "legacy")
    legacy = _call_map(analyzer.analyze(snapshot, module_name))
    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "shared")
    shared = _call_map(analyzer.analyze(snapshot, module_name))
    monkeypatch.setenv(CALL_RESOLUTION_MODE_ENV, "compare")
    compare = _call_map(analyzer.analyze(snapshot, module_name))

    assert shared == legacy
    assert compare == legacy

