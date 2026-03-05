# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.languages.builtin.java import JavaAnalyzer
from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer
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


def _fingerprint(result) -> tuple[tuple, tuple, tuple]:
    nodes = tuple(
        sorted(
            (node.node_type, node.qualified_name, node.start_byte, node.end_byte)
            for node in result.nodes
        )
    )
    edges = tuple(
        sorted(
            (
                edge.src_node_type,
                edge.src_qualified_name,
                edge.edge_type,
                edge.dst_node_type,
                edge.dst_qualified_name,
            )
            for edge in result.edges
        )
    )
    calls = tuple(
        sorted(
            (
                record.node_type,
                record.qualified_name,
                tuple(record.callee_identifiers),
            )
            for record in result.call_records
        )
    )
    return nodes, edges, calls


def test_analyzers_are_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    fixtures = (
        (
            "python",
            PythonAnalyzer(),
            "src/mod.py",
            """
class Service:
    def run(self):
        pass

class Controller:
    def __init__(self):
        self.svc = Service()

    def handle(self):
        self.svc.run()
""",
        ),
        (
            "typescript",
            TypeScriptAnalyzer(),
            "src/mod.ts",
            """
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
""",
        ),
        (
            "javascript",
            JavaScriptAnalyzer(),
            "src/mod.js",
            """
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
""",
        ),
        (
            "java",
            JavaAnalyzer(),
            "src/Mod.java",
            """
package parity;
class Service {
  void run() {}
}
class Controller {
  Service svc = new Service();
  void handle() {
    svc.run();
  }
}
""",
        ),
    )

    for language, analyzer, rel_path, source in fixtures:
        file_path = tmp_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(source, encoding="utf-8")
        snapshot = _snapshot(file_path, rel_path, language, source)
        module_name = analyzer.module_name(tmp_path, snapshot)
        analyzer.module_index = {module_name}

        fingerprints = tuple(
            _fingerprint(analyzer.analyze(snapshot, module_name)) for _ in range(5)
        )
        assert all(fp == fingerprints[0] for fp in fingerprints[1:])


def test_analyzer_bootstrap_diagnostics_are_deterministic() -> None:
    analyzers = [PythonAnalyzer(), TypeScriptAnalyzer(), JavaScriptAnalyzer(), JavaAnalyzer()]
    for analyzer in analyzers:
        diagnostics = getattr(analyzer, "_parser_bootstrap_diagnostics", {})
        assert diagnostics.get("language_name") == analyzer.language
        assert diagnostics.get("query_api_available") is True
        assert diagnostics.get("binding_api") in {"set_language", "language_attr"}
