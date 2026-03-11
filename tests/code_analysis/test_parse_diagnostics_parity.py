# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

import pytest

from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot
from sciona.code_analysis.languages.builtin.java import JavaAnalyzer
from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer
from sciona.code_analysis.languages.builtin.python import PythonAnalyzer
from sciona.code_analysis.languages.builtin.typescript import TypeScriptAnalyzer


EXPECTED_PARSE_DIAGNOSTIC_KEYS = {
    "parse_validation_ok",
    "parse_error_nodes",
    "parse_missing_nodes",
    "parse_significant_missing_nodes",
    "parse_examples",
    "parse_error_summary",
}


def _snapshot(
    repo_root: Path, relative_path: str, source: str, language: str
) -> FileSnapshot:
    file_path = repo_root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(source, encoding="utf-8")
    return FileSnapshot(
        record=FileRecord(
            path=file_path,
            relative_path=Path(relative_path),
            language=language,
        ),
        file_id="file",
        blob_sha="hash",
        size=len(source.encode("utf-8")),
        line_count=source.count("\n"),
        content=source.encode("utf-8"),
    )


@pytest.mark.parametrize(
    ("analyzer_cls", "language", "relative_path", "source"),
    [
        (PythonAnalyzer, "python", "pkg/broken.py", "def broken(:\n    pass\n"),
        (
            TypeScriptAnalyzer,
            "typescript",
            "src/broken.ts",
            "export function broken( {\n",
        ),
        (
            JavaScriptAnalyzer,
            "javascript",
            "src/broken.js",
            "export function broken( {\n",
        ),
        (JavaAnalyzer, "java", "src/Broken.java", "class Broken { void run( { }\n"),
    ],
)
def test_builtin_analyzers_share_parse_diagnostics_schema(
    tmp_path: Path,
    analyzer_cls,
    language: str,
    relative_path: str,
    source: str,
) -> None:
    snapshot = _snapshot(tmp_path, relative_path, source, language)
    analyzer = analyzer_cls()
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}

    result = analyzer.analyze(snapshot, module_name)
    diagnostics = result.diagnostics

    assert EXPECTED_PARSE_DIAGNOSTIC_KEYS.issubset(diagnostics)
    assert diagnostics["parse_validation_ok"] is False
    assert (
        diagnostics["parse_error_nodes"] + diagnostics["parse_significant_missing_nodes"]
    ) >= 1
