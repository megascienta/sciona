# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import ast
import shutil
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from validations.reducers.validation.call_contract import resolve_call_in_contract
from validations.reducers.validation.call_contract import build_contract_call_candidates
from validations.reducers.validation.call_contract import resolve_call_in_contract_details
from validations.reducers.validation.evaluation_resolution import (
    build_independent_call_resolution,
)
from validations.reducers.validation.evaluation_parse import parse_independent_files
from validations.reducers.validation.evaluation import _filter_core_edges_in_contract
from validations.reducers.validation.ground_truth import edge_records_from_ground_truth
from validations.reducers.validation.import_contract import resolve_import_contract
from validations.reducers.validation.import_contract import _load_tsconfig
from validations.reducers.validation.independent.contract_normalization import (
    module_name_from_file,
    normalize_scoped_calls,
)
from sciona.code_analysis.core.extract.languages.typescript import (
    module_name as core_typescript_module_name,
)
from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from validations.reducers.validation.independent.java_runner import _require_core_jar
from validations.reducers.validation.independent.normalize import normalize_file_edges
from validations.reducers.validation.independent.python_ast import parse_python_files
from validations.reducers.validation.independent.python_ast import _CallVisitor
from validations.reducers.validation.independent.ts_node import parse_typescript_files
from validations.reducers.validation.independent.java_runner import parse_java_files
from validations.reducers.validation.independent.shared import (
    Definition,
    EdgeRecord,
    FileParseResult,
    ImportEdge,
    NormalizedCallEdge,
)
from sciona.code_analysis.contracts import select_strict_call_candidate
from validations.reducers.validation.metrics import compute_set_metrics


FIXTURE_ROOT = Path("tests/fixtures/independent")
FIXTURE_MATRIX_PATH = FIXTURE_ROOT / "fixture_matrix.json"


def independent_results_hash(results: dict, normalized_map: dict) -> str:
    serialized = []
    for file_path in sorted(results.keys()):
        result = results[file_path]
        normalized_calls, normalized_imports = normalized_map.get(file_path, ([], []))
        serialized.append(
            {
                "language": result.language,
                "file_path": result.file_path,
                "module_qualified_name": result.module_qualified_name,
                "parse_ok": result.parse_ok,
                "error": result.error,
                "defs": [
                    [definition.kind, definition.qualified_name, definition.start_line, definition.end_line]
                    for definition in result.defs
                ],
                "normalized_call_edges": [
                    [edge.caller, edge.callee, edge.callee_qname, edge.dynamic, edge.callee_text]
                    for edge in normalized_calls
                ],
                "normalized_import_edges": [
                    [edge.source_module, edge.target_module, edge.dynamic]
                    for edge in normalized_imports
                ],
            }
        )
    payload = json.dumps(serialized, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _java_parser_ready() -> bool:
    if shutil.which("javac") is None or shutil.which("java") is None:
        return False
    try:
        jar = Path(_require_core_jar())
    except Exception:
        return False
    return jar.is_file()


def _load_expected(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_fixture_matrix() -> list[dict]:
    payload = json.loads(FIXTURE_MATRIX_PATH.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures")
    assert isinstance(fixtures, list), "fixture_matrix.json must contain a fixtures list"
    return fixtures


def _parse_fixture(language: str, root: Path, file_path: str, module_qualified_name: str):
    files = [{"file_path": file_path, "module_qualified_name": module_qualified_name}]
    if language == "python":
        return parse_python_files(root, files)
    if language == "typescript":
        return parse_typescript_files(root, files)
    if language == "java":
        return parse_java_files(root, files)
    raise AssertionError(f"Unsupported fixture language: {language}")


def _skip_if_fixture_requirements_missing(fixture: dict) -> None:
    requirements = set(fixture.get("requires") or [])
    if "node" in requirements and shutil.which("node") is None:
        pytest.skip("node is required")
    if "java_parser_toolchain" in requirements and not _java_parser_ready():
        pytest.skip("java parser toolchain is not configured")


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


def _normalized_calls_as_dicts(result) -> list[dict]:
    calls, _imports = normalize_file_edges(
        result.module_qualified_name,
        result.call_edges,
        result.import_edges,
    )
    rows = [
        {
            "caller": edge.caller,
            "callee": edge.callee,
            "callee_qname": edge.callee_qname,
            "dynamic": edge.dynamic,
            "callee_text": edge.callee_text,
        }
        for edge in calls
    ]
    rows.sort(
        key=lambda item: (
            item["caller"],
            item["callee"],
            str(item["callee_qname"]),
            item["dynamic"],
            str(item["callee_text"]),
        )
    )
    return rows


def _normalized_imports_as_dicts(result) -> list[dict]:
    _calls, imports = normalize_file_edges(
        result.module_qualified_name,
        result.call_edges,
        result.import_edges,
    )
    rows = [
        {
            "source_module": edge.source_module,
            "target_module": edge.target_module,
            "dynamic": edge.dynamic,
        }
        for edge in imports
    ]
    rows.sort(
        key=lambda item: (item["source_module"], item["target_module"], item["dynamic"])
    )
    return rows


def _assert_optional_normalized_expectations(
    result,
    expected: dict,
    *,
    mode: str,
) -> None:
    expected_calls = expected.get("expected_normalized_calls")
    if expected_calls is not None:
        actual_calls = _normalized_calls_as_dicts(result)
        if mode == "subset":
            assert all(entry in actual_calls for entry in expected_calls)
        else:
            assert actual_calls == expected_calls
    expected_imports = expected.get("expected_normalized_imports")
    if expected_imports is not None:
        actual_imports = _normalized_imports_as_dicts(result)
        if mode == "subset":
            assert all(entry in actual_imports for entry in expected_imports)
        else:
            assert actual_imports == expected_imports


def test_fixture_matrix_quality_gates() -> None:
    fixtures = _load_fixture_matrix()
    assert fixtures, "fixture matrix must not be empty"
    ids = [fixture.get("id") for fixture in fixtures]
    assert len(ids) == len(set(ids)), "fixture ids must be unique"
    languages = {fixture.get("language") for fixture in fixtures}
    assert {"python", "typescript", "java"}.issubset(languages)
    expected_categories = {
        "core_calls",
        "imports",
        "nested_classes",
        "alias_imports",
        "chained_receivers",
        "constructor_injection",
        "namespace_aliases",
        "typed_params",
        "member_resolution",
        "relative_index_imports",
    }
    covered_categories = set()
    for fixture in fixtures:
        fixture_id = fixture.get("id")
        categories = fixture.get("categories") or []
        assert categories, f"fixture {fixture_id} must define categories"
        covered_categories.update(categories)
        root = FIXTURE_ROOT / fixture["root"]
        expected = _load_expected(root / "expected.json")
        assert (
            "expected_normalized_calls" in expected
        ), f"fixture {fixture_id} must define expected_normalized_calls"
        assert (
            "expected_normalized_imports" in expected
        ), f"fixture {fixture_id} must define expected_normalized_imports"
    assert expected_categories.issubset(covered_categories)


@pytest.mark.parametrize(
    "fixture",
    _load_fixture_matrix(),
    ids=lambda item: item["id"],
)
def test_independent_parser_fixture_matrix_differential(fixture: dict) -> None:
    _skip_if_fixture_requirements_missing(fixture)
    root = FIXTURE_ROOT / fixture["root"]
    results = _parse_fixture(
        fixture["language"],
        root,
        fixture["file_path"],
        fixture["module_qualified_name"],
    )
    assert len(results) == 1
    result = results[0]
    expected = _load_expected(root / "expected.json")
    assert fixture.get("categories"), f"Fixture {fixture['id']} must define categories"
    mode = fixture.get("assert_mode", "subset")
    if mode == "exact":
        _assert_fixture_exact(result, expected)
    elif mode == "subset":
        _assert_fixture(result, expected)
    else:
        raise AssertionError(f"Unknown assert_mode for fixture {fixture['id']}: {mode}")
    _assert_optional_normalized_expectations(result, expected, mode=mode)


@pytest.mark.parametrize(
    "fixture",
    _load_fixture_matrix(),
    ids=lambda item: item["id"],
)
def test_independent_parser_fixture_matrix_hash_stability(fixture: dict) -> None:
    _skip_if_fixture_requirements_missing(fixture)
    root = FIXTURE_ROOT / fixture["root"]
    file_path = fixture["file_path"]
    module_qualified_name = fixture["module_qualified_name"]
    results1_list = _parse_fixture(
        fixture["language"], root, file_path, module_qualified_name
    )
    results2_list = _parse_fixture(
        fixture["language"], root, file_path, module_qualified_name
    )
    results1 = {entry.file_path: entry for entry in results1_list}
    results2 = {entry.file_path: entry for entry in results2_list}
    normalized1 = {
        path: normalize_file_edges(res.module_qualified_name, res.call_edges, res.import_edges)
        for path, res in results1.items()
    }
    normalized2 = {
        path: normalize_file_edges(res.module_qualified_name, res.call_edges, res.import_edges)
        for path, res in results2.items()
    }
    assert independent_results_hash(results1, normalized1) == independent_results_hash(
        results2, normalized2
    )


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


def test_python_parser_nested_class_fixture() -> None:
    root = FIXTURE_ROOT / "python_nested"
    files = [{"file_path": "sample.py", "module_qualified_name": "fixture.sample"}]
    result = parse_python_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture_exact(result, expected)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_nested_class_fixture() -> None:
    root = FIXTURE_ROOT / "typescript_nested"
    files = [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    result = parse_typescript_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture_exact(result, expected)


@pytest.mark.skipif(
    not _java_parser_ready(),
    reason="java parser toolchain is not configured",
)
def test_java_parser_fixture() -> None:
    root = FIXTURE_ROOT / "java"
    files = [{"file_path": "Sample.java", "module_qualified_name": "fixture.sample"}]
    result = parse_java_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture(result, expected)


@pytest.mark.skipif(
    not _java_parser_ready(),
    reason="java parser toolchain is not configured",
)
def test_java_parser_nested_class_fixture() -> None:
    root = FIXTURE_ROOT / "java_nested"
    files = [{"file_path": "Sample.java", "module_qualified_name": "fixture.sample"}]
    result = parse_java_files(root, files)[0]
    expected = _load_expected(root / "expected.json")
    _assert_fixture(result, expected)


@pytest.mark.skipif(
    not _java_parser_ready(),
    reason="java parser toolchain is not configured",
)
def test_java_parser_emits_assignment_hints() -> None:
    root = FIXTURE_ROOT / "java_constructor_field"
    files = [{"file_path": "Sample.java", "module_qualified_name": "fixture.sample"}]
    result = parse_java_files(root, files)[0]
    assert result.parse_ok
    assert any(hint.scope == "fixture.sample.Sample.Sample" for hint in result.assignment_hints)
    assert any(hint.receiver == "service" for hint in result.assignment_hints)


@pytest.mark.skipif(
    not _java_parser_ready(),
    reason="java parser toolchain is not configured",
)
def test_java_parser_collects_declared_type_assignment_hints(tmp_path: Path) -> None:
    source = tmp_path / "Sample.java"
    source.write_text(
        "package fixture.sample;\n"
        "class Service { void run() {} }\n"
        "class Controller {\n"
        "  private Service service;\n"
        "  void handle(Service svc) {\n"
        "    Service local = svc;\n"
        "    local.run();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_java_files(
        tmp_path, [{"file_path": "Sample.java", "module_qualified_name": "fixture.sample"}]
    )[0]
    assert result.parse_ok
    hints = {(h.scope, h.receiver, h.value_text) for h in result.assignment_hints}
    assert ("fixture.sample.Controller.constructor", "this.service", "Service") in hints
    assert ("fixture.sample.Controller.handle", "svc", "Service") in hints
    assert ("fixture.sample.Controller.handle", "local", "Service") in hints


@pytest.mark.skipif(
    not _java_parser_ready(),
    reason="java parser toolchain is not configured",
)
def test_java_parser_collects_method_reference_calls(tmp_path: Path) -> None:
    source = tmp_path / "Sample.java"
    source.write_text(
        "package fixture.sample;\n"
        "import java.util.List;\n"
        "class Controller {\n"
        "  void run(String item) {}\n"
        "  void handle(List<String> items) {\n"
        "    items.forEach(this::run);\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_java_files(
        tmp_path, [{"file_path": "Sample.java", "module_qualified_name": "fixture.sample"}]
    )[0]
    assert result.parse_ok
    edges = {(edge.caller, edge.callee) for edge in result.call_edges}
    assert ("fixture.sample.Controller.handle", "run") in edges


def test_scoped_call_normalization_is_module_and_language_local() -> None:
    alpha_calls = [
        NormalizedCallEdge(
            caller="repo.pkg.alpha.fn",
            callee="run",
            callee_qname="repo.pkg.alpha.Service.run",
            dynamic=False,
        ),
        NormalizedCallEdge(
            caller="repo.pkg.alpha.fn2",
            callee="run",
            callee_qname="repo.pkg.alpha.Other.run",
            dynamic=False,
        ),
    ]
    beta_calls = [
        NormalizedCallEdge(
            caller="repo.pkg.beta.fn",
            callee="run",
            callee_qname="repo.pkg.beta.Service.run",
            dynamic=False,
        )
    ]
    alpha = normalize_scoped_calls(alpha_calls, language="python", module_scope="repo.pkg.alpha")
    beta = normalize_scoped_calls(beta_calls, language="python", module_scope="repo.pkg.beta")
    # Ambiguous terminal in same scope must collapse to terminal only.
    assert alpha[0].callee_qname is None
    assert alpha[0].callee == "run"
    assert beta[0].callee_qname == "repo.pkg.beta.Service.run"


def test_import_contract_typescript_relative_index_fallback() -> None:
    resolved = resolve_import_contract(
        raw_target="./api",
        file_path="pkg/main.ts",
        module_qname="fixture.pkg.main",
        language="typescript",
        module_names={"fixture.pkg.api.index"},
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.pkg.api.index"


def test_import_contract_python_relative_package_resolution() -> None:
    resolved = resolve_import_contract(
        raw_target=".utils",
        file_path="pkg/mod.py",
        module_qname="fixture.pkg.mod",
        language="python",
        module_names={"fixture.pkg.utils"},
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.pkg.utils"


def test_import_contract_java_package_prefix_resolution(tmp_path: Path) -> None:
    src = tmp_path / "src" / "main" / "java" / "org" / "example"
    src.mkdir(parents=True)
    (src / "Main.java").write_text("package org.example;\nclass Main {}\n", encoding="utf-8")
    resolved = resolve_import_contract(
        raw_target="org.example.dep.Type",
        file_path="src/main/java/org/example/Main.java",
        module_qname="fixture.src.main.java.org.example.Main",
        language="java",
        module_names={"fixture.src.main.java.org.example.dep.Type"},
        repo_root=tmp_path,
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.src.main.java.org.example.dep.Type"


def test_metrics_deduplicates_neighbor_edges() -> None:
    expected = [
        EdgeRecord(caller="a.mod.fn", callee="b", callee_qname="pkg.b"),
        EdgeRecord(caller="a.mod.fn", callee="b", callee_qname="pkg.b"),
    ]
    actual = [EdgeRecord(caller="a.mod.fn", callee="b", callee_qname="pkg.b")]
    metrics = compute_set_metrics(expected, actual)
    assert metrics.intersection_count == 1
    assert metrics.missing_count == 0
    assert metrics.coverage == 1.0


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
    expected_filtered, full_truth, _, _, _ = edge_records_from_ground_truth(
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
        },
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
    assert independent_results_hash(results1, normalized1) == independent_results_hash(
        results2, normalized2
    )


def test_typescript_import_contract_resolves_relative_index() -> None:
    module_names = {
        "fixture.pkg.api.index",
        "fixture.pkg.api.client",
    }
    resolved = resolve_import_contract(
        raw_target="./api",
        file_path="pkg/main.ts",
        module_qname="fixture.pkg.main",
        language="typescript",
        module_names=module_names,
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.pkg.api.index"


def test_typescript_import_contract_resolves_tsconfig_path_alias(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "baseUrl": ".",
                    "paths": {"@app/*": ["src/*"]},
                }
            }
        ),
        encoding="utf-8",
    )
    resolved = resolve_import_contract(
        raw_target="@app/utils",
        file_path="src/main.ts",
        module_qname="fixture.src.main",
        language="typescript",
        module_names={"fixture.src.utils"},
        repo_root=tmp_path,
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.src.utils"


def test_load_tsconfig_is_cached(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "baseUrl": ".",
                    "paths": {"@app/*": ["src/*"]},
                }
            }
        ),
        encoding="utf-8",
    )
    _load_tsconfig.cache_clear()
    first = _load_tsconfig(tmp_path)
    second = _load_tsconfig(tmp_path)
    assert first is second


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_parse_independent_files_canonicalizes_typescript_module_scope(tmp_path: Path) -> None:
    source = tmp_path / "pkg" / "main.ts"
    source.parent.mkdir(parents=True)
    source.write_text(
        "const helper = () => 1;\n"
        "export function run() { return helper(); }\n",
        encoding="utf-8",
    )
    parse_map = {
        "pkg/main.ts": {
            "file_path": "pkg/main.ts",
            "module_qualified_name": "wrong.scope",
            "language": "typescript",
        }
    }
    results = parse_independent_files(tmp_path, parse_map, on_file_parsed=None)
    parsed = results["pkg/main.ts"]
    expected_module = module_name_from_file(tmp_path, "pkg/main.ts", "typescript")
    assert parsed.module_qualified_name == expected_module
    assert any(edge.caller == f"{expected_module}.run" for edge in parsed.call_edges)


def test_ground_truth_excludes_external_imports_from_enrichment() -> None:
    file_result = FileParseResult(
        language="python",
        file_path="pkg/mod.py",
        module_qualified_name="fixture.pkg.mod",
        defs=[],
        call_edges=[],
        import_edges=[ImportEdge("fixture.pkg.mod", "requests", False)],
        assignment_hints=[],
        parse_ok=True,
    )
    normalized_calls, normalized_imports = normalize_file_edges(
        file_result.module_qualified_name, file_result.call_edges, file_result.import_edges
    )
    entity = SimpleNamespace(
        kind="module",
        qualified_name="fixture.sample",
        module_qualified_name="fixture.sample",
    )
    _, _, out_of_contract, out_meta, _ = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=normalized_imports,
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.sample"},
        call_resolution={},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert out_meta == []
    assert out_of_contract == []


def test_ground_truth_excludes_out_of_repo_calls_from_enrichment() -> None:
    file_result = FileParseResult(
        language="python",
        file_path="pkg/mod.py",
        module_qualified_name="fixture.pkg.mod",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    normalized_calls = [
        NormalizedCallEdge(
            caller="fixture.pkg.mod.fn",
            callee="print",
            callee_qname=None,
            dynamic=False,
            callee_text="print(x)",
        )
    ]
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.pkg.mod.fn",
        module_qualified_name="fixture.pkg.mod",
    )
    expected, _, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.pkg.mod"},
        call_resolution={"symbol_index": {}},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert out_of_contract == []
    assert out_meta == []
    assert diagnostics["excluded_out_of_scope_by_reason"].get("external") == 1


def test_ground_truth_partitions_baskets_when_same_edge_has_conflicting_reasons() -> None:
    file_result = FileParseResult(
        language="python",
        file_path="pkg/mod.py",
        module_qualified_name="fixture.pkg.mod",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    normalized_calls = [
        # Same caller/callee key appears first as dynamic, then as external call.
        NormalizedCallEdge(
            caller="fixture.pkg.mod.fn",
            callee="print",
            callee_qname=None,
            dynamic=True,
            callee_text="obj.print()",
        ),
        NormalizedCallEdge(
            caller="fixture.pkg.mod.fn",
            callee="print",
            callee_qname=None,
            dynamic=False,
            callee_text="print(x)",
        ),
    ]
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.pkg.mod.fn",
        module_qualified_name="fixture.pkg.mod",
    )
    expected, _, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.pkg.mod"},
        call_resolution={"symbol_index": {}},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert out_of_contract == []
    assert out_meta == []
    assert len(diagnostics["contract_exclusion_edges_full"]) == 1
    assert diagnostics["excluded_out_of_scope_by_reason"].get("external") == 1
    assert diagnostics["included_limitation_count"] == 0
    assert diagnostics["limitation_edges_full"] == []


def test_ground_truth_includes_dynamic_and_unresolved_in_expanded_tiers() -> None:
    file_result = FileParseResult(
        language="python",
        file_path="pkg/mod.py",
        module_qualified_name="fixture.pkg.mod",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    normalized_calls = [
        NormalizedCallEdge(
            caller="fixture.pkg.mod.fn",
            callee="local_call",
            callee_qname=None,
            dynamic=False,
            callee_text="local_call()",
        ),
        NormalizedCallEdge(
            caller="fixture.pkg.mod.fn",
            callee="dyn_call",
            callee_qname=None,
            dynamic=True,
            callee_text="obj.dyn_call()",
        ),
    ]
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.pkg.mod.fn",
        module_qualified_name="fixture.pkg.mod",
    )
    expected, _, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.pkg.mod"},
        call_resolution={
            "symbol_index": {
                "local_call": [
                    "fixture.pkg.mod.a.local_call",
                    "fixture.pkg.mod.b.local_call",
                ]
            }
        },
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert len(out_of_contract) == 2
    reasons = {m["reason"] for m in out_meta}
    assert "dynamic" in reasons
    assert any(reason.startswith("in_repo_unresolved") for reason in reasons)
    assert "in_repo_unresolved_ambiguous_no_in_scope_candidate" in reasons
    high = diagnostics["limitation_edges_high_conf"]
    full = diagnostics["limitation_edges_full"]
    assert len(high) == 1
    assert len(full) == 2
    unresolved_count = sum(
        count
        for reason, count in diagnostics["included_limitation_by_reason"].items()
        if reason.startswith("in_repo_unresolved")
    )
    assert unresolved_count == 1
    assert diagnostics["included_limitation_by_reason"]["dynamic"] == 1


def test_ground_truth_excludes_resolved_unresolved_static_from_q2_reference() -> None:
    file_result = FileParseResult(
        language="typescript",
        file_path="pkg/hook.ts",
        module_qualified_name="fixture.pkg.hook",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    normalized_calls = [
        NormalizedCallEdge(
            caller="fixture.pkg.hook.callHook",
            callee="getNonAliasProviders",
            callee_qname="module.getNonAliasProviders",
            dynamic=False,
            callee_text="module.getNonAliasProviders()",
        )
    ]
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.pkg.hook.callHook",
        module_qualified_name="fixture.pkg.hook",
    )
    call_resolution = {
        "symbol_index": {
            "getNonAliasProviders": [
                "fixture.pkg.injector.module.Module.getNonAliasProviders"
            ]
        },
        "module_lookup": {
            "fixture.pkg.injector.module.Module.getNonAliasProviders": "fixture.pkg.injector.module"
        },
        "import_targets": {"fixture.pkg.hook": {"fixture.pkg.injector.module"}},
    }
    expected, _, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.pkg.hook", "fixture.pkg.injector.module"},
        call_resolution=call_resolution,
        repo_root=FIXTURE_ROOT / "typescript",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert len(out_of_contract) == 1
    assert out_of_contract[0].callee_qname == "module.getNonAliasProviders"
    assert out_meta and out_meta[0]["reason"].startswith("in_repo_unresolved")
    unresolved_count = sum(
        count
        for reason, count in diagnostics["included_limitation_by_reason"].items()
        if reason.startswith("in_repo_unresolved")
    )
    assert unresolved_count == 1


def test_ground_truth_nest_hook_like_partition_is_deterministic() -> None:
    file_result = FileParseResult(
        language="typescript",
        file_path="packages/core/hooks/on-app-shutdown.hook.ts",
        module_qualified_name="nest.packages.core.hooks.on-app-shutdown.hook",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    caller = "nest.packages.core.hooks.on-app-shutdown.hook.callAppShutdownHook"
    normalized_calls = [
        NormalizedCallEdge(
            caller=caller,
            callee="callOperator",
            callee_qname="nest.packages.core.hooks.on-app-shutdown.hook.callOperator",
            dynamic=False,
            callee_text="callOperator()",
        ),
        NormalizedCallEdge(
            caller=caller,
            callee="hasOnAppShutdownHook",
            callee_qname="nest.packages.core.hooks.on-app-shutdown.hook.hasOnAppShutdownHook",
            dynamic=False,
            callee_text="hasOnAppShutdownHook()",
        ),
        NormalizedCallEdge(
            caller=caller,
            callee="getNonAliasProviders",
            callee_qname="module.getNonAliasProviders",
            dynamic=False,
            callee_text="module.getNonAliasProviders()",
        ),
        NormalizedCallEdge(
            caller=caller,
            callee="isDependencyTreeStatic",
            callee_qname="moduleClassHost.isDependencyTreeStatic",
            dynamic=False,
            callee_text="moduleClassHost.isDependencyTreeStatic()",
        ),
        NormalizedCallEdge(
            caller=caller,
            callee="all",
            callee_qname="Promise.all",
            dynamic=False,
            callee_text="Promise.all()",
        ),
    ]
    entity = SimpleNamespace(
        kind="function",
        qualified_name=caller,
        module_qualified_name="nest.packages.core.hooks.on-app-shutdown.hook",
    )
    call_resolution = {
        "symbol_index": {
            "callOperator": [
                "nest.packages.core.hooks.on-app-shutdown.hook.callOperator"
            ],
            "hasOnAppShutdownHook": [
                "nest.packages.core.hooks.on-app-shutdown.hook.hasOnAppShutdownHook"
            ],
            "getNonAliasProviders": [
                "nest.packages.core.injector.module.Module.getNonAliasProviders"
            ],
            "isDependencyTreeStatic": [
                "nest.packages.core.injector.instance-wrapper.InstanceWrapper.isDependencyTreeStatic"
            ],
        },
        "module_lookup": {
            "nest.packages.core.hooks.on-app-shutdown.hook.callOperator": "nest.packages.core.hooks.on-app-shutdown.hook",
            "nest.packages.core.hooks.on-app-shutdown.hook.hasOnAppShutdownHook": "nest.packages.core.hooks.on-app-shutdown.hook",
            "nest.packages.core.injector.module.Module.getNonAliasProviders": "nest.packages.core.injector.module",
            "nest.packages.core.injector.instance-wrapper.InstanceWrapper.isDependencyTreeStatic": "nest.packages.core.injector.instance-wrapper",
        },
        "import_targets": {
            "nest.packages.core.hooks.on-app-shutdown.hook": {
                "nest.packages.core.injector.module",
                "nest.packages.core.injector.instance-wrapper",
            }
        },
    }
    expected, _, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={
            "nest.packages.core.hooks.on-app-shutdown.hook",
            "nest.packages.core.injector.module",
            "nest.packages.core.injector.instance-wrapper",
        },
        call_resolution=call_resolution,
        repo_root=FIXTURE_ROOT / "typescript",
        repo_prefix="nest",
        local_packages={"nest"},
    )
    assert {
        edge.callee_qname
        for edge in expected
    } == {
        "nest.packages.core.hooks.on-app-shutdown.hook.callOperator",
        "nest.packages.core.hooks.on-app-shutdown.hook.hasOnAppShutdownHook",
    }
    assert {edge.callee_qname for edge in out_of_contract} == {
        "module.getNonAliasProviders",
        "moduleClassHost.isDependencyTreeStatic",
    }
    assert all(item["reason"].startswith("in_repo_unresolved") for item in out_meta)
    unresolved_count = sum(
        count
        for reason, count in diagnostics["included_limitation_by_reason"].items()
        if reason.startswith("in_repo_unresolved")
    )
    assert unresolved_count == 2
    assert diagnostics["excluded_out_of_scope_by_reason"]["external"] == 1


def test_ground_truth_treats_decorator_shaped_calls_as_dynamic() -> None:
    file_result = FileParseResult(
        language="python",
        file_path="pkg/mod.py",
        module_qualified_name="fixture.pkg.mod",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    normalized_calls = [
        NormalizedCallEdge(
            caller="fixture.pkg.mod.fn",
            callee="cache",
            callee_qname=None,
            dynamic=True,
            callee_text="decorator:cache()",
        ),
    ]
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.pkg.mod.fn",
        module_qualified_name="fixture.pkg.mod",
    )
    expected, _, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=normalized_calls,
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.pkg.mod"},
        call_resolution={"symbol_index": {}},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert len(out_of_contract) == 1
    assert out_meta and out_meta[0]["reason"] == "decorator"
    assert out_meta[0]["semantic_type"] == "decorator_call"
    assert diagnostics["included_limitation_by_reason"]["decorator"] == 1


def test_ground_truth_class_diagnostic_marks_no_method_class() -> None:
    file_result = FileParseResult(
        language="python",
        file_path="pkg/mod.py",
        module_qualified_name="fixture.pkg.mod",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    entity = SimpleNamespace(
        kind="class",
        qualified_name="fixture.pkg.mod.Empty",
        module_qualified_name="fixture.pkg.mod",
    )
    expected, full, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=[],
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.pkg.mod"},
        call_resolution={},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert full == []
    assert out_of_contract == []
    assert out_meta == []
    assert diagnostics["class_has_methods"] is False


def test_ground_truth_class_uses_direct_method_ownership_only() -> None:
    file_result = FileParseResult(
        language="java",
        file_path="src/Sample.java",
        module_qualified_name="fixture.src.Sample",
        defs=[
            Definition(
                kind="class",
                qualified_name="fixture.src.Sample.Outer",
                start_line=1,
                end_line=100,
            ),
            Definition(
                kind="class",
                qualified_name="fixture.src.Sample.Outer.Inner",
                start_line=10,
                end_line=40,
            ),
            Definition(
                kind="method",
                qualified_name="fixture.src.Sample.Outer.outerMethod",
                start_line=2,
                end_line=5,
            ),
            Definition(
                kind="method",
                qualified_name="fixture.src.Sample.Outer.Inner.innerMethod",
                start_line=12,
                end_line=15,
            ),
        ],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    entity = SimpleNamespace(
        kind="class",
        qualified_name="fixture.src.Sample.Outer",
        module_qualified_name="fixture.src.Sample",
        start_line=1,
        end_line=100,
    )
    expected, full, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=[],
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.src.Sample"},
        call_resolution={},
        repo_root=FIXTURE_ROOT / "java",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert out_of_contract == []
    assert out_meta == []
    assert diagnostics["class_match_strategy"] == "exact_qname"
    assert diagnostics["class_truth_method_count"] == 1
    assert [edge.callee_qname for edge in expected] == ["fixture.src.Sample.Outer.outerMethod"]
    assert [edge.callee_qname for edge in full] == ["fixture.src.Sample.Outer.outerMethod"]


def test_ground_truth_class_marks_ambiguous_match_unreliable() -> None:
    file_result = FileParseResult(
        language="java",
        file_path="src/Sample.java",
        module_qualified_name="fixture.src.Sample",
        defs=[
            Definition(
                kind="class",
                qualified_name="fixture.src.Sample.Outer.Target",
                start_line=1,
                end_line=10,
                simple_name="Target",
                enclosing_class_qname="fixture.src.Sample.Outer",
            ),
            Definition(
                kind="class",
                qualified_name="fixture.src.Sample.Other.Target",
                start_line=20,
                end_line=30,
                simple_name="Target",
                enclosing_class_qname="fixture.src.Sample.Other",
            ),
        ],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    entity = SimpleNamespace(
        kind="class",
        qualified_name="fixture.src.Sample.Target",
        module_qualified_name="fixture.src.Sample",
    )
    expected, full, out_of_contract, out_meta, diagnostics = edge_records_from_ground_truth(
        file_result=file_result,
        normalized_calls=[],
        normalized_imports=[],
        module_imports_by_prefix={},
        entity=entity,
        module_names={"fixture.src.Sample"},
        call_resolution={},
        repo_root=FIXTURE_ROOT / "java",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert full == []
    assert out_of_contract == []
    assert out_meta == []
    assert diagnostics["class_match_strategy"] == "ambiguous"
    assert diagnostics["class_truth_unreliable"] is True


def test_python_parser_collects_assignment_hints() -> None:
    tree = ast.parse(
        "class Service:\n"
        "    def run(self):\n"
        "        return 1\n"
        "\n"
        "def entry():\n"
        "    svc = Service()\n"
        "    return svc.run()\n"
    )
    visitor = _CallVisitor("fixture.sample")
    visitor.visit(tree)
    hints = {(h.scope, h.receiver, h.value_text) for h in visitor.assignment_hints}
    assert ("fixture.sample.entry", "svc", "Service") in hints


def test_python_parser_collects_parameter_annotation_hints() -> None:
    tree = ast.parse(
        "from fixture.websocket import WebSocket\n"
        "def endpoint(websocket: WebSocket):\n"
        "    websocket.accept()\n"
    )
    visitor = _CallVisitor("fixture.sample")
    visitor.visit(tree)
    hints = {(h.scope, h.receiver, h.value_text) for h in visitor.assignment_hints}
    assert ("fixture.sample.endpoint", "websocket", "WebSocket") in hints


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_collects_assignment_hints(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "class Service { run() {} }\n"
        "function entry() {\n"
        "  const svc = new Service();\n"
        "  return svc.run();\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    hints = {(h.scope, h.receiver, h.value_text) for h in result.assignment_hints}
    assert ("fixture.sample.entry", "svc", "Service") in hints


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_collects_constructor_parameter_property_hints(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "class Service { run() {} }\n"
        "class Controller {\n"
        "  constructor(private service: Service) {}\n"
        "  handle() { return this.service.run(); }\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    hints = {(h.scope, h.receiver, h.value_text) for h in result.assignment_hints}
    assert (
        "fixture.sample.Controller.constructor",
        "this.service",
        "Service",
    ) in hints


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_preserves_curried_call_callee_identity(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "enum RouteParamtypes { FILE }\n"
        "const createPipesRouteParamDecorator = (paramtype: RouteParamtypes) =>\n"
        "  (data?: any) => data;\n"
        "export function UploadedFile(fileKey?: string) {\n"
        "  return createPipesRouteParamDecorator(RouteParamtypes.FILE)(fileKey);\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    assert result.parse_ok
    uploaded_edges = [
        edge for edge in result.call_edges if edge.caller == "fixture.sample.UploadedFile"
    ]
    assert any(edge.callee == "createPipesRouteParamDecorator" for edge in uploaded_edges)
    assert not any(edge.callee == "FILE" for edge in uploaded_edges)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_unwraps_casted_receiver_calls(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "type Ref = { forwardRef?: () => { name?: string } };\n"
        "export const getName = (instance: unknown): string | undefined => {\n"
        "  return (instance as Ref)?.forwardRef?.()?.name;\n"
        "};\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    assert result.parse_ok
    edges = [edge for edge in result.call_edges if edge.caller == "fixture.sample.getName"]
    assert edges
    assert any(edge.callee == "forwardRef" for edge in edges)
    assert any((edge.callee_text or "").endswith("forwardRef") for edge in edges)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_collects_type_annotation_assignment_hints(
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "class Service { run() {} }\n"
        "class Controller {\n"
        "  private service: Service;\n"
        "  handle(svc: Service) {\n"
        "    const local: Service = svc;\n"
        "    return local.run();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    hints = {(h.scope, h.receiver, h.value_text) for h in result.assignment_hints}
    assert ("fixture.sample.Controller.constructor", "this.service", "Service") in hints
    assert ("fixture.sample.Controller.handle", "svc", "Service") in hints
    assert ("fixture.sample.Controller.handle", "local", "Service") in hints


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_collects_accessor_method_defs(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "class Controller {\n"
        "  get value() { return 1; }\n"
        "  set value(v: number) {}\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    defs = {entry.qualified_name for entry in result.defs if entry.kind == "method"}
    assert "fixture.sample.Controller.value" in defs


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_collects_default_export_anonymous_function(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "const logger = { info() {} };\n"
        "export default function () {\n"
        "  logger.info();\n"
        "}\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    assert result.parse_ok
    defs = {entry.qualified_name for entry in result.defs if entry.kind == "function"}
    assert "fixture.sample.default" in defs
    edges = [edge for edge in result.call_edges if edge.caller == "fixture.sample.default"]
    assert any(edge.callee == "info" for edge in edges)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_typescript_parser_collects_export_assignment_arrow_function(tmp_path: Path) -> None:
    source = tmp_path / "sample.ts"
    source.write_text(
        "const logger = { info() {} };\n"
        "export default () => {\n"
        "  logger.info();\n"
        "};\n",
        encoding="utf-8",
    )
    result = parse_typescript_files(
        tmp_path, [{"file_path": "sample.ts", "module_qualified_name": "fixture.sample"}]
    )[0]
    assert result.parse_ok
    defs = {entry.qualified_name for entry in result.defs if entry.kind == "function"}
    assert "fixture.sample.default" in defs
    edges = [edge for edge in result.call_edges if edge.caller == "fixture.sample.default"]
    assert any(edge.callee == "info" for edge in edges)


def test_call_contract_resolves_module_scoped_symbol() -> None:
    edge = NormalizedCallEdge(
        caller="fixture.sample.entry",
        callee="run",
        callee_qname=None,
        dynamic=False,
        callee_text="svc.run",
    )
    resolved = resolve_call_in_contract(
        edge=edge,
        caller_qname="fixture.sample.entry",
        caller_module="fixture.sample",
        call_resolution={
            "symbol_index": {"run": ["fixture.sample.Service.run"]},
            "module_lookup": {"fixture.sample.Service.run": "fixture.sample"},
            "import_targets": {"fixture.sample": set()},
        },
    )
    assert resolved == "fixture.sample.Service.run"


def test_call_contract_does_not_guess_ambiguous_class_leaf() -> None:
    edge = NormalizedCallEdge(
        caller="fixture.sample.entry",
        callee="run",
        callee_qname=None,
        dynamic=False,
        callee_text="Service.run",
    )
    resolved = resolve_call_in_contract(
        edge=edge,
        caller_qname="fixture.sample.entry",
        caller_module="fixture.sample",
        call_resolution={
            "symbol_index": {
                "run": ["fixture.sample.alpha.Service.run", "fixture.sample.beta.Service.run"]
            },
            "module_lookup": {
                "fixture.sample.alpha.Service.run": "fixture.sample.alpha",
                "fixture.sample.beta.Service.run": "fixture.sample.beta",
            },
            "import_targets": {"fixture.sample": set()},
        },
    )
    assert resolved is None


def test_call_resolution_output_is_core_contract_minimal() -> None:
    file_result = FileParseResult(
        language="typescript",
        file_path="sample.ts",
        module_qualified_name="fixture.sample",
        defs=[
            Definition(kind="class", qualified_name="fixture.sample.Service", start_line=1, end_line=3),
            Definition(
                kind="method",
                qualified_name="fixture.sample.Service.run",
                start_line=2,
                end_line=2,
            ),
            Definition(
                kind="class",
                qualified_name="fixture.sample.Controller",
                start_line=5,
                end_line=15,
            ),
            Definition(
                kind="method",
                qualified_name="fixture.sample.Controller.constructor",
                start_line=6,
                end_line=8,
            ),
            Definition(
                kind="method",
                qualified_name="fixture.sample.Controller.handle",
                start_line=10,
                end_line=12,
            ),
        ],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    resolution = build_independent_call_resolution(
        independent_results={file_result.file_path: file_result},
        normalized_edge_map={file_result.file_path: ([], [])},
        module_names={"fixture.sample"},
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert set(resolution.keys()) == {"mode", "symbol_index", "module_lookup", "import_targets"}


def test_class_edge_filter_does_not_drop_valid_class_methods() -> None:
    entity = SimpleNamespace(
        kind="class",
        qualified_name="fixture.sample.Controller",
        module_qualified_name="fixture.sample",
        language="typescript",
    )
    edges = [
        EdgeRecord(
            caller="fixture.sample.Controller",
            callee="handle",
            callee_qname="fixture.sample.Controller.handle",
        ),
        EdgeRecord(
            caller="fixture.sample.Controller",
            callee="constructor",
            callee_qname="fixture.sample.Controller.constructor",
        ),
    ]
    filtered = _filter_core_edges_in_contract(
        entity=entity,
        edges=edges,
        call_resolution={},
        module_names={"fixture.sample"},
    )
    assert len(filtered) == 2


def test_callable_edge_filter_ignores_unknown_reducer_qname_hint() -> None:
    entity = SimpleNamespace(
        kind="function",
        qualified_name="fixture.sample.fn",
        module_qualified_name="fixture.sample",
        language="python",
    )
    edges = [
        EdgeRecord(
            caller="fixture.sample.fn",
            callee="run",
            callee_qname="fixture.unknown.Service.run",
        )
    ]
    filtered = _filter_core_edges_in_contract(
        entity=entity,
        edges=edges,
        call_resolution={
            "module_lookup": {"fixture.sample.Service.run": "fixture.sample"},
            "symbol_index": {"run": ["fixture.sample.Service.run"]},
            "import_targets": {"fixture.sample": set()},
        },
        module_names={"fixture.sample"},
    )
    assert len(filtered) == 1
    assert filtered[0].callee_qname == "fixture.sample.Service.run"


def test_call_resolution_seeds_java_callable_index_from_all_nodes() -> None:
    file_result = FileParseResult(
        language="java",
        file_path="sample.py",
        module_qualified_name="fixture.sample",
        defs=[],
        call_edges=[],
        import_edges=[],
        assignment_hints=[],
        parse_ok=True,
    )
    resolution = build_independent_call_resolution(
        independent_results={file_result.file_path: file_result},
        normalized_edge_map={file_result.file_path: ([], [])},
        module_names={"fixture.sample"},
        repo_root=Path("/tmp/fixture"),
        repo_prefix="fixture",
        local_packages={"fixture"},
        all_nodes=[
            {
                "node_type": "function",
                "qualified_name": "fixture.sample.helper",
                "module_qualified_name": "fixture.sample",
                "language": "java",
            },
            {
                "node_type": "method",
                "qualified_name": "fixture.sample.Service.run",
                "module_qualified_name": "fixture.sample",
                "language": "java",
            },
        ],
    )
    assert "helper" in resolution["symbol_index"]
    assert "fixture.sample.helper" in resolution["symbol_index"]["helper"]
    assert resolution["module_lookup"]["fixture.sample.Service.run"] == "fixture.sample"


def test_call_contract_keeps_same_module_ambiguity_unresolved() -> None:
    edge = NormalizedCallEdge(
        caller="fixture.sample.entry",
        callee="run",
        callee_qname=None,
        dynamic=False,
        callee_text="run",
    )
    resolved = resolve_call_in_contract(
        edge=edge,
        caller_qname="fixture.sample.entry",
        caller_module="fixture.sample",
        call_resolution={
            "symbol_index": {
                "run": [
                    "fixture.sample.Service.run",
                    "fixture.sample.Other.run",
                ]
            },
            "module_lookup": {
                "fixture.sample.Service.run": "fixture.sample",
                "fixture.sample.Other.run": "fixture.sample",
            },
            "import_targets": {"fixture.sample": set()},
        },
    )
    assert resolved is None


def test_call_contract_details_use_shared_strict_selector() -> None:
    edge = NormalizedCallEdge(
        caller="fixture.sample.entry",
        callee="run",
        callee_qname=None,
        dynamic=False,
        callee_text="svc.run",
    )
    call_resolution = {
        "symbol_index": {
            "run": [
                "fixture.sample.Service.run",
                "fixture.sample.Other.run",
            ]
        },
        "module_lookup": {
            "fixture.sample.Service.run": "fixture.sample",
            "fixture.sample.Other.run": "fixture.sample",
        },
        "import_targets": {"fixture.sample": set()},
    }
    details = resolve_call_in_contract_details(
        edge=edge,
        caller_qname="fixture.sample.entry",
        caller_module="fixture.sample",
        call_resolution=call_resolution,
    )
    candidates = build_contract_call_candidates(
        edge=edge,
        caller_qname="fixture.sample.entry",
        caller_module="fixture.sample",
        call_resolution=call_resolution,
    )
    expected = select_strict_call_candidate(
        identifier=candidates.identifier,
        direct_candidates=candidates.direct_candidates,
        fallback_candidates=candidates.fallback_candidates,
        caller_module="fixture.sample",
        module_lookup=call_resolution["module_lookup"],
        import_targets=call_resolution["import_targets"],
    )
    assert details.callee_qname == expected.accepted_candidate
    assert details.accepted_provenance == expected.accepted_provenance


def test_call_contract_accepts_placeholder_member_qname_via_core_candidates() -> None:
    edge = NormalizedCallEdge(
        caller="fixture.pkg.hook.callHook",
        callee="getNonAliasProviders",
        callee_qname="module.getNonAliasProviders",
        dynamic=False,
        callee_text="module.getNonAliasProviders()",
    )
    call_resolution = {
        "symbol_index": {
            "getNonAliasProviders": [
                "fixture.pkg.injector.module.Module.getNonAliasProviders"
            ]
        },
        "module_lookup": {
            "fixture.pkg.injector.module.Module.getNonAliasProviders": "fixture.pkg.injector.module"
        },
        "import_targets": {"fixture.pkg.hook": {"fixture.pkg.injector.module"}},
    }
    details = resolve_call_in_contract_details(
        edge=edge,
        caller_qname="fixture.pkg.hook.callHook",
        caller_module="fixture.pkg.hook",
        call_resolution=call_resolution,
    )
    assert details.callee_qname == "fixture.pkg.injector.module.Module.getNonAliasProviders"
    assert details.accepted_provenance == "import_narrowed"


def test_typescript_module_name_parity_for_d_ts_and_tsx(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir(parents=True)
    dts_path = src / "types.d.ts"
    dts_path.write_text("export type T = string;\n", encoding="utf-8")
    tsx_path = src / "view.tsx"
    tsx_path.write_text("export const V = () => null;\n", encoding="utf-8")

    dts_snapshot = FileSnapshot(
        record=FileRecord(
            path=dts_path,
            relative_path=Path("src/types.d.ts"),
            language="typescript",
        ),
        file_id="file1",
        blob_sha="hash1",
        size=10,
        line_count=1,
        content=b"x",
    )
    tsx_snapshot = FileSnapshot(
        record=FileRecord(
            path=tsx_path,
            relative_path=Path("src/view.tsx"),
            language="typescript",
        ),
        file_id="file2",
        blob_sha="hash2",
        size=10,
        line_count=1,
        content=b"x",
    )

    assert core_typescript_module_name(tmp_path, dts_snapshot) == module_name_from_file(
        tmp_path, "src/types.d.ts", "typescript"
    )
    assert core_typescript_module_name(tmp_path, tsx_snapshot) == module_name_from_file(
        tmp_path, "src/view.tsx", "typescript"
    )
