# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.core.normalize.model import FileRecord, FileSnapshot
from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer


def _snapshot(repo: Path, relative_path: str, content: str) -> FileSnapshot:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return FileSnapshot(
        record=FileRecord(
            path=path,
            relative_path=Path(relative_path),
            language="javascript",
        ),
        file_id=relative_path,
        blob_sha="h",
        size=len(content.encode("utf-8")),
        line_count=content.count("\n") + 1,
        content=content.encode("utf-8"),
    )


def test_javascript_analyzer_extracts_declared_nested_and_bound_callables(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        export function outer() {
          function inner() { helper(); }
          const bound = () => inner();
          [1,2,3].map((x) => x + 1);
          return bound();
        }
        export function helper() {}
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    callables = {node.qualified_name for node in result.nodes if node.node_type == "callable"}
    assert f"{module_name}.outer" in callables
    assert f"{module_name}.outer.inner" in callables
    assert f"{module_name}.outer.bound" in callables
    assert f"{module_name}.helper" in callables
    assert all(not name.endswith(".x") for name in callables)

    by_caller = {record.qualified_name: set(record.callee_identifiers) for record in result.call_records}
    assert f"{module_name}.helper" in by_caller[f"{module_name}.outer.inner"]


def test_javascript_analyzer_promotes_class_field_arrow_callable(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        export class C {
          f = () => this.g();
          g() { return 1; }
        }
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    callable_nodes = {
        node.qualified_name: (node.metadata or {}).get("callable_role")
        for node in result.nodes
        if node.node_type == "callable"
    }
    assert callable_nodes[f"{module_name}.C.f"] == "bound"
    assert callable_nodes[f"{module_name}.C.g"] == "declared"


def test_javascript_analyzer_collects_imports_require_and_dynamic_import(tmp_path) -> None:
    repo = tmp_path
    utils_snapshot = _snapshot(repo, "src/utils.js", "export function helper() { return 1; }\n")
    mod_snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        import { helper } from './utils';
        const utils = require('./utils');
        export async function run() {
          const dynamic = await import('./utils');
          return helper() + utils.helper() + dynamic.helper();
        }
        """,
    )
    analyzer = JavaScriptAnalyzer()
    mod_module = analyzer.module_name(repo, mod_snapshot)
    utils_module = analyzer.module_name(repo, utils_snapshot)
    analyzer.module_index = {mod_module, utils_module}
    result = analyzer.analyze(mod_snapshot, mod_module)

    import_targets = {
        edge.dst_qualified_name
        for edge in result.edges
        if edge.edge_type == "IMPORTS_DECLARED"
    }
    assert utils_module in import_targets

    by_caller = {record.qualified_name: set(record.callee_identifiers) for record in result.call_records}
    assert f"{utils_module}.helper" in by_caller[f"{mod_module}.run"]
