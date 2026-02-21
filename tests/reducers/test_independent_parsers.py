# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.reducers.reducer_validation import _independent_results_hash
from experiments.reducers.validation.ground_truth import edge_records_from_ground_truth
from experiments.reducers.validation.import_contract import resolve_import_contract
from experiments.reducers.validation.independent.normalize import normalize_file_edges
from experiments.reducers.validation.independent.python_ast import parse_python_files
from experiments.reducers.validation.independent.ts_node import parse_typescript_files
from experiments.reducers.validation.independent.java_runner import parse_java_files
from experiments.reducers.validation.independent.shared import EdgeRecord
from experiments.reducers.validation.metrics import compute_metrics


FIXTURE_ROOT = Path("tests/fixtures/independent")


def _load_expected(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_fixture(result, expected: dict) -> None:
    defs = {entry.qualified_name for entry in result.defs}
    call_callees = {entry.callee for entry in result.call_edges}
    import_targets = {entry.target_module for entry in result.import_edges}
    assert result.parse_ok
    assert set(expected["defs"]).issubset(defs)
    assert set(expected["call_callees"]).issubset(call_callees)
    assert set(expected["import_targets"]).issubset(import_targets)


def _assert_fixture_exact(result, expected: dict) -> None:
    defs = {entry.qualified_name for entry in result.defs}
    call_callees = {entry.callee for entry in result.call_edges}
    import_targets = {entry.target_module for entry in result.import_edges}
    assert result.parse_ok
    assert defs == set(expected["defs"])
    assert call_callees == set(expected["call_callees"])
    assert import_targets == set(expected["import_targets"])


def test_python_parser_fixture() -> None:
    root = FIXTURE_ROOT / "python"
    files = [{"file_path": "sample.py", "module_qualified_name": "fixture.sample"}]
    result = parse_python_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture(result, expected)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_fixture() -> None:
    root = FIXTURE_ROOT / "typescript"
    files = [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    result = parse_typescript_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture_exact(result, expected)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_reexport_fixture() -> None:
    root = FIXTURE_ROOT / "typescript_reexports"
    files = [{"file_path": "barrel.ts", "module_qualified_name": "fixture.barrel"}]
    result = parse_typescript_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture_exact(result, expected)


@pytest.mark.skipif(
    not os.environ.get("SCIONA_JAVAPARSER_JAR")
    or shutil.which("javac") is None
    or shutil.which("java") is None,
    reason="java parser toolchain is not configured",
)
def test_java_parser_fixture() -> None:
    root = FIXTURE_ROOT / "java"
    files = [{"file_path": "Sample.java", "module_qualified_name": "fixture.sample"}]
    result = parse_java_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture(result, expected)


def test_metrics_deduplicates_neighbor_edges() -> None:
    expected = [
        EdgeRecord(caller="a.mod.fn", callee="b", callee_qname="pkg.b"),
        EdgeRecord(caller="a.mod.fn", callee="b", callee_qname="pkg.b"),
    ]
    actual = [EdgeRecord(caller="a.mod.fn", callee="b", callee_qname="pkg.b")]
    metrics = compute_metrics(expected, [], actual)
    assert metrics.tp == 1
    assert metrics.fn == 0
    assert metrics.in_contract_recall == 1.0


def test_ground_truth_dedupes_duplicate_calls() -> None:
    file_result = parse_python_files(
        FIXTURE_ROOT / "python",
        [{"file_path": "sample.py", "module_qualified_name": "fixture.sample"}],
    )[0]
    normalized_calls, normalized_imports = normalize_file_edges(
        file_result.module_qualified_name,
        file_result.call_edges + file_result.call_edges,
        file_result.import_edges,
    )
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.sample.entry",
        module_qualified_name="fixture.sample",
    )
    expected_filtered, full_truth, _, _ = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=normalized_imports,
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.sample"},
        call_resolution={
            "symbol_index": {"run": ["fixture.sample.Service.run"]},
            "module_lookup": {"fixture.sample.Service.run": "fixture.sample"},
            "import_targets": {"fixture.sample": set()},
            "class_name_index": {"Service": ["fixture.sample.Service"]},
            "class_method_index": {"fixture.sample.Service": {"run": "fixture.sample.Service.run"}},
            "module_symbol_index": {"fixture.sample": {"run": ["fixture.sample.Service.run"]}},
            "import_symbol_hints": {},
            "namespace_aliases": {},
        },
        contract={"call_contract": {"require_callee_in_repo": True}},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert len(full_truth) == len({(e.caller, e.callee, e.callee_qname) for e in full_truth})
    assert len(expected_filtered) == len(
        {(e.caller, e.callee, e.callee_qname) for e in expected_filtered}
    )


def test_parser_hash_is_stable() -> None:
    root = FIXTURE_ROOT / "python"
    files = [{"file_path": "sample.py", "module_qualified_name": "fixture.sample"}]
    results1 = {entry.file_path: entry for entry in parse_python_files(root, files)}
    normalized1 = {
        path: normalize_file_edges(res.module_qualified_name, res.call_edges, res.import_edges)
        for path, res in results1.items()
    }
    results2 = {entry.file_path: entry for entry in parse_python_files(root, files)}
    normalized2 = {
        path: normalize_file_edges(res.module_qualified_name, res.call_edges, res.import_edges)
        for path, res in results2.items()
    }
    assert _independent_results_hash(results1, normalized1) == _independent_results_hash(
        results2, normalized2
    )


def test_typescript_import_contract_resolves_relative_index() -> None:
    module_names = {
        "fixture.pkg.api.index",
        "fixture.pkg.api.client",
    }
    contract = {
        "imports": {
            "require_module_in_repo": True,
            "languages": {"typescript": {"resolver": "typescript_normalize"}},
        }
    }
    resolved = resolve_import_contract(
        raw_target="./api",
        file_path="pkg/main.ts",
        module_qname="fixture.pkg.main",
        language="typescript",
        contract=contract,
        module_names=module_names,
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.pkg.api.index"
