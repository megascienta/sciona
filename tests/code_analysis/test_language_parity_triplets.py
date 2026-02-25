# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from pathlib import Path

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


def test_triplet_service_fixture_parity(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/parity/triplet_service")
    expected = json.loads((fixture_root / "expected.json").read_text(encoding="utf-8"))

    language_specs = (
        ("python", "python.py", PythonAnalyzer(), "python"),
        ("typescript", "typescript.ts", TypeScriptAnalyzer(), "typescript"),
        ("java", "java.java", JavaAnalyzer(), "java"),
    )

    for rel_dir, fixture_name, analyzer, language in language_specs:
        source = (fixture_root / fixture_name).read_text(encoding="utf-8")
        ext = ".py" if language == "python" else (".java" if language == "java" else ".ts")
        rel_path = f"{rel_dir}/mod{ext}"
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")

        snapshot = _snapshot(path, rel_path, language, source)
        module_name = analyzer.module_name(tmp_path, snapshot)
        analyzer.module_index = {module_name}
        result = analyzer.analyze(snapshot, module_name)

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
