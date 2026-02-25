# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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


def _scenario_roots() -> list[Path]:
    roots = [Path("tests/fixtures/parity/triplet_service"), *sorted(Path("tests/fixtures/parity/generated").iterdir())]
    return [path for path in roots if path.is_dir() and (path / "expected.json").exists()]


def test_language_parity_score_gate(tmp_path: Path) -> None:
    language_specs = (
        ("python", "python.py", PythonAnalyzer(), "python"),
        ("typescript", "typescript.ts", TypeScriptAnalyzer(), "typescript"),
        ("java", "java.java", JavaAnalyzer(), "java"),
    )

    score_by_language: dict[str, list[float]] = {lang: [] for lang, *_ in language_specs}
    node_score_by_language: dict[str, list[float]] = {lang: [] for lang, *_ in language_specs}
    call_score_by_language: dict[str, list[float]] = {lang: [] for lang, *_ in language_specs}

    for scenario in _scenario_roots():
        expected = json.loads((scenario / "expected.json").read_text(encoding="utf-8"))
        for language, fixture_name, analyzer, _ in language_specs:
            source = (scenario / fixture_name).read_text(encoding="utf-8")
            ext = ".py" if language == "python" else (".java" if language == "java" else ".ts")
            rel_path = f"{scenario.name}/{language}/mod{ext}"
            path = tmp_path / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
            snapshot = _snapshot(path, rel_path, language, source)
            module_name = analyzer.module_name(tmp_path, snapshot)
            analyzer.module_index = {module_name}
            result = analyzer.analyze(snapshot, module_name)

            qnames = {node.qualified_name for node in result.nodes}
            node_expect = max(1, len(expected["node_suffixes"]))
            node_hits = sum(
                1 for suffix in expected["node_suffixes"] if f"{module_name}.{suffix}" in qnames
            )
            node_score = node_hits / node_expect

            call_map = {
                record.qualified_name: set(record.callee_identifiers)
                for record in result.call_records
            }
            call_expect = max(1, len(expected["call_assertions"]))
            call_hits = 0
            for assertion in expected["call_assertions"]:
                caller = f"{module_name}.{assertion['caller_suffix']}"
                callee = f"{module_name}.{assertion['callee_suffix']}"
                if caller in call_map and callee in call_map[caller]:
                    call_hits += 1
            call_score = call_hits / call_expect

            score = (node_score + call_score) / 2.0
            score_by_language[language].append(score)
            node_score_by_language[language].append(node_score)
            call_score_by_language[language].append(call_score)

    for language in ("python", "typescript", "java"):
        avg_score = sum(score_by_language[language]) / len(score_by_language[language])
        avg_node = sum(node_score_by_language[language]) / len(node_score_by_language[language])
        avg_call = sum(call_score_by_language[language]) / len(call_score_by_language[language])
        assert avg_score >= 0.95, f"{language} parity score below threshold: {avg_score:.3f}"
        assert avg_node >= 0.90, f"{language} node parity below critical threshold: {avg_node:.3f}"
        assert avg_call >= 0.90, f"{language} call parity below critical threshold: {avg_call:.3f}"

