# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.languages.builtin.java import JavaAnalyzer
from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer
from sciona.code_analysis.languages.builtin.python import PythonAnalyzer
from sciona.code_analysis.languages.builtin.typescript import TypeScriptAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot


def build_snapshot(path: Path, rel: str, language: str, content: str) -> FileSnapshot:
    return FileSnapshot(
        record=FileRecord(path=path, relative_path=Path(rel), language=language),
        file_id="file",
        blob_sha="hash",
        size=len(content.encode("utf-8")),
        line_count=content.count("\n"),
        content=content.encode("utf-8"),
    )


def language_specs():
    return (
        ("python", "python.py", PythonAnalyzer(), "python"),
        ("typescript", "typescript.ts", TypeScriptAnalyzer(), "typescript"),
        ("javascript", "javascript.js", JavaScriptAnalyzer(), "javascript"),
        ("java", "java.java", JavaAnalyzer(), "java"),
    )


def extension_for(language: str) -> str:
    if language == "python":
        return ".py"
    if language == "java":
        return ".java"
    if language == "javascript":
        return ".js"
    return ".ts"


def assert_parity_expectations(result, module_name: str, expected: dict[str, object]) -> None:
    qnames = {node.qualified_name for node in result.nodes}
    for suffix in expected["node_suffixes"]:
        assert f"{module_name}.{suffix}" in qnames

    call_map = {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }
    for assertion in expected["call_assertions"]:
        caller = f"{module_name}.{assertion['caller_suffix']}"
        callee = f"{module_name}.{assertion['callee_suffix']}"
        assert caller in call_map
        assert callee in call_map[caller]
