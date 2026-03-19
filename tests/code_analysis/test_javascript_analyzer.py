# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

import pytest

from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot
from sciona.code_analysis.languages.builtin.javascript import JavaScriptAnalyzer
from sciona.code_analysis.languages.builtin.javascript.javascript_node_walk import (
    _javascript_heritage_metadata,
)


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


def test_javascript_heritage_metadata_preserves_expression_commas() -> None:
    class _Node:
        def __init__(self, node_type: str, text: str = "", children=None):
            self.type = node_type
            self._text = text.encode("utf-8")
            self.named_children = list(children or [])

        def child_by_field_name(self, name: str):
            return None

        @property
        def text(self):
            return self._text

    node = _Node(
        "class_declaration",
        children=[_Node("extends_clause", "extends mix(BaseA, BaseB)")],
    )

    metadata = _javascript_heritage_metadata(node, b"")

    assert metadata["bases"] == ["mix(BaseA, BaseB)"]


def test_javascript_analyzer_reports_malformed_parse_tree(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(repo, "src/broken.js", "export function broken( {\n")
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}

    result = analyzer.analyze(snapshot, module_name)
    diagnostics = result.diagnostics
    assert diagnostics["parse_validation_ok"] is False
    assert (
        diagnostics["parse_error_nodes"] + diagnostics["parse_significant_missing_nodes"]
    ) >= 1
    assert diagnostics["parse_error_summary"]
    assert any(node.qualified_name == module_name for node in result.nodes)


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


def test_javascript_analyzer_strict_gate_drops_external_import_calls(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        import { helper } from 'third-party-lib';
        export function run() {
          return helper();
        }
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    call_map = {record.qualified_name: tuple(record.callee_identifiers) for record in result.call_records}
    assert call_map == {}


def test_javascript_analyzer_does_not_promote_inline_or_iife_callables(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        export function outer(items) {
          const mapped = items.map((x) => x + 1);
          (function () { return 1; })();
          return mapped;
        }
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    callables = {node.qualified_name for node in result.nodes if node.node_type == "callable"}
    assert f"{module_name}.outer" in callables
    assert all(not name.endswith(".x") for name in callables)
    assert all(".default" not in name for name in callables)


def test_javascript_analyzer_does_not_promote_dynamic_destructured_binding(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        export function outer(factory) {
          ({ f } = factory());
          return f;
        }
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    callables = {node.qualified_name for node in result.nodes if node.node_type == "callable"}
    assert f"{module_name}.outer" in callables
    assert all(not name.endswith(".f") for name in callables if name != f"{module_name}.outer")


def test_javascript_analyzer_disambiguates_duplicate_bound_callable_names(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        export function outer() {
          const f = () => 1;
          const f = () => 2;
          return f();
        }
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    callables = {node.qualified_name for node in result.nodes if node.node_type == "callable"}
    assert f"{module_name}.outer.f" in callables
    assert f"{module_name}.outer.f-2" in callables


def test_javascript_analyzer_promotes_static_assignment_surfaces(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        class Holder {}
        exports.run = function run() { return 1; };
        module.exports.load = () => 2;
        Tools.build = function build() { return 3; };
        Holder.Factory = class Factory {
          make() { return 4; }
        };
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    nodes = {
        node.qualified_name: node.node_type
        for node in result.nodes
        if node.node_type in {"callable", "classifier"}
    }
    assert nodes[f"{module_name}.run"] == "callable"
    assert nodes[f"{module_name}.load"] == "callable"
    assert nodes[f"{module_name}.Tools.build"] == "callable"
    assert nodes[f"{module_name}.Holder.Factory"] == "classifier"
    assert nodes[f"{module_name}.Holder.Factory.make"] == "callable"


def test_javascript_analyzer_does_not_promote_computed_assignment_surfaces(tmp_path) -> None:
    repo = tmp_path
    snapshot = _snapshot(
        repo,
        "src/mod.js",
        """
        const name = "run";
        exports[name] = function run() { return 1; };
        module.exports["load"] = () => 2;
        """,
    )
    analyzer = JavaScriptAnalyzer()
    module_name = analyzer.module_name(repo, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)

    names = {node.qualified_name for node in result.nodes}
    assert f"{module_name}.run" not in names
    assert f"{module_name}.load" not in names
