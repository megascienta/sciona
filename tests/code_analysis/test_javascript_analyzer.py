# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


def test_javascript_analyzer_emits_module_node(tmp_path):
    repo = tmp_path
    src = repo / "src"
    src.mkdir()
    file_path = src / "mod.js"
    file_path.write_text("export const x = 1;\n", encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path("src/mod.js"),
            language="javascript",
        ),
        file_id="f1",
        blob_sha="h",
        size=1,
        line_count=1,
        content=file_path.read_bytes(),
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    result = analyzer.analyze(snapshot, module_name)
    assert len(result.nodes) == 1
    assert result.nodes[0].node_type == "module"
    assert result.nodes[0].qualified_name.endswith(".src.mod")
