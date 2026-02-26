# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sciona.code_analysis.core.extract.languages.java import JavaAnalyzer
from sciona.code_analysis.core.extract.languages.python import PythonAnalyzer
from sciona.code_analysis.core.extract.languages.typescript import TypeScriptAnalyzer
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from validations.reducers.validation.independent.java_runner import (
    _require_core_jar,
    parse_java_files,
)
from validations.reducers.validation.independent.python_ast import parse_python_files
from validations.reducers.validation.independent.ts_node import parse_typescript_files
from validations.reducers.validation.raw_edge_schema import (
    CanonicalRawCallEdge,
    call_key,
    canonicalize_call_edge,
    canonicalize_import_edge_with_default,
    validate_call_schema,
    validate_import_schema,
)


FIXTURE_ROOT = Path("tests/fixtures/independent")
FIXTURE_MATRIX_PATH = FIXTURE_ROOT / "fixture_matrix.json"


def _core_snapshot(path: Path, file_path: str, language: str) -> FileSnapshot:
    content = path.read_text(encoding="utf-8")
    return FileSnapshot(
        record=FileRecord(path=path, relative_path=Path(file_path), language=language),
        file_id="fixture",
        blob_sha="fixture",
        size=len(content.encode("utf-8")),
        line_count=max(1, content.count("\n")),
        content=content.encode("utf-8"),
    )


def _load_fixture_matrix() -> list[dict]:
    payload = json.loads(FIXTURE_MATRIX_PATH.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures")
    assert isinstance(fixtures, list)
    return fixtures


def _skip_for_requirements(fixture: dict) -> None:
    requirements = set(fixture.get("requires") or [])
    if "node" in requirements and shutil.which("node") is None:
        pytest.skip("node is required")
    if "java_parser_toolchain" in requirements:
        if shutil.which("javac") is None or shutil.which("java") is None:
            pytest.skip("java toolchain is required")
        try:
            _require_core_jar()
        except Exception:
            pytest.skip("SCIONA_JAVAPARSER_JAR is required")


def _parse_independent_fixture(fixture: dict):
    language = fixture["language"]
    root = FIXTURE_ROOT / fixture["root"]
    entry = {
        "file_path": fixture["file_path"],
        "module_qualified_name": fixture["module_qualified_name"],
    }
    if language == "python":
        return parse_python_files(root, [entry])[0], root
    if language == "typescript":
        return parse_typescript_files(root, [entry])[0], root
    if language == "java":
        return parse_java_files(root, [entry])[0], root
    raise AssertionError(f"unsupported language: {language}")


def _project_core_calls(fixture: dict, root: Path) -> set[tuple[str, str]]:
    language = fixture["language"]
    source_path = root / fixture["file_path"]
    module_name = fixture["module_qualified_name"]
    snapshot = _core_snapshot(source_path, fixture["file_path"], language)
    if language == "python":
        analyzer = PythonAnalyzer()
    elif language == "typescript":
        analyzer = TypeScriptAnalyzer()
    elif language == "java":
        analyzer = JavaAnalyzer()
    else:
        raise AssertionError(f"unsupported language: {language}")
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    projected: set[tuple[str, str]] = set()
    for record in result.call_records:
        for identifier in record.callee_identifiers:
            terminal = identifier.split(".")[-1]
            projected.add((record.qualified_name, terminal))
    return projected


def _canonical_independent_calls(raw_calls) -> list[CanonicalRawCallEdge]:
    return [canonicalize_call_edge(edge) for edge in raw_calls]


def test_independent_raw_edges_follow_canonical_schema() -> None:
    fixtures = _load_fixture_matrix()
    for fixture in fixtures:
        _skip_for_requirements(fixture)
        result, _root = _parse_independent_fixture(fixture)
        assert result.parse_ok, fixture["id"]

        for edge in _canonical_independent_calls(result.call_edges):
            errors = validate_call_schema(edge)
            assert not errors, f"{fixture['id']} invalid call edge {edge}: {errors}"

        for edge in [
            canonicalize_import_edge_with_default(
                item, default_source_module=result.module_qualified_name
            )
            for item in result.import_edges
        ]:
            errors = validate_import_schema(edge)
            assert not errors, f"{fixture['id']} invalid import edge {edge}: {errors}"


def test_independent_raw_call_edges_have_core_projection_overlap() -> None:
    fixtures = _load_fixture_matrix()
    by_language_overlap: dict[str, list[float]] = {}
    for fixture in fixtures:
        _skip_for_requirements(fixture)
        result, root = _parse_independent_fixture(fixture)
        if not result.parse_ok:
            continue
        independent_keys = {
            call_key(edge)
            for edge in _canonical_independent_calls(result.call_edges)
            if edge.caller and edge.callee
        }
        core_keys = _project_core_calls(fixture, root)
        if not core_keys:
            continue
        overlap = len(independent_keys & core_keys) / len(core_keys)
        by_language_overlap.setdefault(fixture["language"], []).append(overlap)
        assert overlap >= 0.90, (
            f"{fixture['id']} core-call overlap too low: {overlap:.3f} "
            f"(core={len(core_keys)} indep={len(independent_keys)})"
        )

    for language, scores in by_language_overlap.items():
        avg = sum(scores) / len(scores)
        assert avg >= 0.95, f"{language} average raw-call overlap below gate: {avg:.3f}"
