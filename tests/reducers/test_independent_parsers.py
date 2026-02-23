# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import ast
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.reducers.reducer_validation import _independent_results_hash
from experiments.reducers.validation.call_contract import resolve_call_in_contract
from experiments.reducers.validation.ground_truth import edge_records_from_ground_truth
from experiments.reducers.validation.import_contract import resolve_import_contract
from experiments.reducers.validation.independent.contract_normalization import (
    normalize_scoped_calls,
)
from experiments.reducers.validation.independent.java_runner import _require_jar
from experiments.reducers.validation.independent.normalize import normalize_file_edges
from experiments.reducers.validation.independent.python_ast import parse_python_files
from experiments.reducers.validation.independent.python_ast import _CallVisitor
from experiments.reducers.validation.independent.ts_node import parse_typescript_files
from experiments.reducers.validation.independent.java_runner import parse_java_files
from experiments.reducers.validation.independent.shared import (
    Definition,
    EdgeRecord,
    FileParseResult,
    ImportEdge,
    NormalizedCallEdge,
)
from experiments.reducers.validation.metrics import compute_metrics


FIXTURE_ROOT = Path("tests/fixtures/independent")


def _java_parser_ready() -> bool:
    if shutil.which("javac") is None or shutil.which("java") is None:
        return False
    try:
        jar = Path(_require_jar())
    except Exception:
        return False
    return jar.is_file()


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
        contract={
            "imports": {
                "require_module_in_repo": True,
                "languages": {"typescript": {"resolver": "typescript_normalize"}},
            }
        },
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
        contract={
            "imports": {
                "require_module_in_repo": True,
                "languages": {"python": {"resolver": "python_resolve"}},
            }
        },
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
        contract={
            "imports": {
                "require_module_in_repo": True,
                "languages": {"java": {"resolver": "java_normalize"}},
            }
        },
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
    contract = {
        "imports": {
            "require_module_in_repo": True,
            "languages": {"typescript": {"resolver": "typescript_normalize"}},
        }
    }
    resolved = resolve_import_contract(
        raw_target="@app/utils",
        file_path="src/main.ts",
        module_qname="fixture.src.main",
        language="typescript",
        contract=contract,
        module_names={"fixture.src.utils"},
        repo_root=tmp_path,
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert resolved == "fixture.src.utils"


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
        contract={
            "imports": {
                "require_module_in_repo": True,
                "languages": {"python": {"resolver": "python_resolve"}},
            }
        },
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert out_meta == []
    assert out_of_contract == []


def test_ground_truth_excludes_standard_calls_from_enrichment() -> None:
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
        contract={"out_of_contract": {"standard_calls": ["print"]}},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert out_of_contract == []
    assert out_meta == []
    assert diagnostics["excluded_out_of_scope_by_reason"].get("standard_call") == 1


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
        contract={"out_of_contract": {"standard_calls": []}},
        repo_root=FIXTURE_ROOT / "python",
        repo_prefix="fixture",
        local_packages={"fixture"},
    )
    assert expected == []
    assert len(out_of_contract) == 2
    assert {m["reason"] for m in out_meta} == {"in_repo_unresolved", "dynamic"}
    high = diagnostics["limitation_edges_high_conf"]
    full = diagnostics["limitation_edges_full"]
    assert len(high) == 1
    assert len(full) == 2
    assert diagnostics["included_limitation_by_reason"]["in_repo_unresolved"] == 1
    assert diagnostics["included_limitation_by_reason"]["dynamic"] == 1


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
        contract={},
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
        contract={},
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
        contract={},
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


def test_call_contract_resolves_receiver_binding() -> None:
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
            "class_name_index": {"Service": ["fixture.sample.Service"]},
            "class_method_index": {"fixture.sample.Service": {"run": "fixture.sample.Service.run"}},
            "module_symbol_index": {"fixture.sample": {"run": ["fixture.sample.Service.run"]}},
            "import_symbol_hints": {},
            "namespace_aliases": {},
            "receiver_bindings": {"fixture.sample.entry": {"svc": ["fixture.sample.Service"]}},
        },
        contract={"call_contract": {"require_callee_in_repo": True}},
    )
    assert resolved == "fixture.sample.Service.run"
