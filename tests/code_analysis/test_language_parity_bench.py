# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.languages.builtin.java import JavaAnalyzer
from sciona.code_analysis.languages.builtin.python import PythonAnalyzer
from sciona.code_analysis.languages.builtin.typescript import TypeScriptAnalyzer
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


def test_language_parity_service_call_resolution(tmp_path):
    repo = tmp_path

    py_src = """
class Service:
    def run(self):
        pass

class Controller:
    def __init__(self):
        self.svc = Service()
    def handle(self):
        self.svc.run()
"""
    py_path = repo / "py" / "mod.py"
    py_path.parent.mkdir(parents=True)
    py_path.write_text(py_src, encoding="utf-8")
    py = PythonAnalyzer()
    py_snap = _snapshot(py_path, "py/mod.py", "python", py_src)
    py_mod = py.module_name(repo, py_snap)
    py.module_index = {py_mod}
    py_res = py.analyze(py_snap, py_mod)
    py_calls = {r.qualified_name: set(r.callee_identifiers) for r in py_res.call_records}
    assert f"{py_mod}.Service.run" in py_calls[f"{py_mod}.Controller.handle"]

    ts_src = """
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
    ts_path = repo / "ts" / "mod.ts"
    ts_path.parent.mkdir(parents=True)
    ts_path.write_text(ts_src, encoding="utf-8")
    ts = TypeScriptAnalyzer()
    ts_snap = _snapshot(ts_path, "ts/mod.ts", "typescript", ts_src)
    ts_mod = ts.module_name(repo, ts_snap)
    ts.module_index = {ts_mod}
    ts_res = ts.analyze(ts_snap, ts_mod)
    ts_calls = {r.qualified_name: set(r.callee_identifiers) for r in ts_res.call_records}
    assert f"{ts_mod}.Service.run" in ts_calls[f"{ts_mod}.Controller.handle"]

    java_src = """
package a;
class Service {
  void run() {}
}
class Controller {
  Service svc = new Service();
  void handle() {
    svc.run();
  }
}
"""
    java_path = repo / "java" / "Mod.java"
    java_path.parent.mkdir(parents=True)
    java_path.write_text(java_src, encoding="utf-8")
    java = JavaAnalyzer()
    java_snap = _snapshot(java_path, "java/Mod.java", "java", java_src)
    java_mod = java.module_name(repo, java_snap)
    java.module_index = {java_mod}
    java_res = java.analyze(java_snap, java_mod)
    java_calls = {r.qualified_name: set(r.callee_identifiers) for r in java_res.call_records}
    assert f"{java_mod}.Service.run" in java_calls[f"{java_mod}.Controller.handle"]
