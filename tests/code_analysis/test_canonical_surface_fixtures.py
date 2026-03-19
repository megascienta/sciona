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
from sciona.code_analysis.languages.common.support.walker_capabilities import (
    build_walker_capabilities,
)


def _snapshot(repo: Path, relative_path: str, language: str, content: str) -> FileSnapshot:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return FileSnapshot(
        record=FileRecord(path=path, relative_path=Path(relative_path), language=language),
        file_id=relative_path,
        blob_sha="h",
        size=len(content.encode("utf-8")),
        line_count=content.count("\n") + 1,
        content=content.encode("utf-8"),
    )


def _analyzer_for(language: str):
    return {
        "python": PythonAnalyzer,
        "typescript": TypeScriptAnalyzer,
        "javascript": JavaScriptAnalyzer,
        "java": JavaAnalyzer,
    }[language]()


def _node_qnames(result, node_type: str) -> set[str]:
    return {
        node.qualified_name
        for node in result.nodes
        if node.node_type == node_type
    }


def _edge_tuples(result) -> set[tuple[str, str, str]]:
    return {
        (edge.src_qualified_name, edge.edge_type, edge.dst_qualified_name)
        for edge in result.edges
    }


def _call_targets(result) -> dict[str, set[str]]:
    return {
        record.qualified_name: set(record.callee_identifiers)
        for record in result.call_records
    }


def _assert_python_class_declaration(result, module_name: str) -> None:
    assert f"{module_name}.Widget" in _node_qnames(result, "classifier")


def _assert_python_function_declaration(result, module_name: str) -> None:
    assert f"{module_name}.run" in _node_qnames(result, "callable")


def _assert_python_bound_callable(result, module_name: str) -> None:
    assert f"{module_name}.build" in _node_qnames(result, "callable")


def _assert_python_decorated_definition(result, module_name: str) -> None:
    assert f"{module_name}.decorated" in _node_qnames(result, "callable")


def _assert_python_local_inheritance(result, module_name: str) -> None:
    assert (
        f"{module_name}.Child",
        "EXTENDS",
        f"{module_name}.Base",
    ) in _edge_tuples(result)


def _assert_typescript_class_like(result, module_name: str) -> None:
    qnames = _node_qnames(result, "classifier")
    assert f"{module_name}.Shape" in qnames
    assert f"{module_name}.Base" in qnames
    assert f"{module_name}.Child" in qnames


def _assert_typescript_callable_declaration(result, module_name: str) -> None:
    qnames = _node_qnames(result, "callable")
    assert f"{module_name}.run" in qnames
    assert f"{module_name}.Shape.check" in qnames
    assert f"{module_name}.Base.load" in qnames
    assert f"{module_name}.Child.work" in qnames


def _assert_typescript_expression_constructs(result, module_name: str) -> None:
    qnames = _node_qnames(result, "callable") | _node_qnames(result, "classifier")
    assert f"{module_name}.helper" in qnames
    assert f"{module_name}.make" in qnames
    assert f"{module_name}.Factory" in qnames


def _assert_typescript_instance_tracking(result, module_name: str) -> None:
    calls = _call_targets(result)
    assert f"{module_name}.Service.run" in calls[f"{module_name}.handle"]


def _assert_typescript_local_inheritance(result, module_name: str) -> None:
    edges = _edge_tuples(result)
    assert (f"{module_name}.Child", "EXTENDS", f"{module_name}.Base") in edges
    assert (f"{module_name}.Child", "IMPLEMENTS", f"{module_name}.Role") in edges
    assert (f"{module_name}.Local", "EXTENDS", f"{module_name}.Base") in edges


def _assert_java_class_like(result, module_name: str) -> None:
    qnames = _node_qnames(result, "classifier")
    assert f"{module_name}.Base" in qnames
    assert f"{module_name}.Role" in qnames
    assert f"{module_name}.Mode" in qnames
    assert f"{module_name}.Point" in qnames


def _assert_java_method_like(result, module_name: str) -> None:
    qnames = _node_qnames(result, "callable")
    assert f"{module_name}.Widget.Widget" in qnames
    assert f"{module_name}.Widget.run" in qnames
    assert f"{module_name}.Point.Point" in qnames


def _assert_java_field_tracking(result, module_name: str) -> None:
    calls = _call_targets(result)
    assert f"{module_name}.Service.run" in calls[f"{module_name}.Holder.handle"]


def _assert_java_local_inheritance(result, module_name: str) -> None:
    edges = _edge_tuples(result)
    assert (f"{module_name}.Child", "EXTENDS", f"{module_name}.Base") in edges
    assert (f"{module_name}.Child", "IMPLEMENTS", f"{module_name}.Role") in edges


def _assert_javascript_class_declaration(result, module_name: str) -> None:
    qnames = _node_qnames(result, "classifier")
    assert f"{module_name}.Base" in qnames
    assert f"{module_name}.Local" in qnames


def _assert_javascript_callable_declaration(result, module_name: str) -> None:
    qnames = _node_qnames(result, "callable")
    assert f"{module_name}.run" in qnames
    assert f"{module_name}.Widget.handle" in qnames


def _assert_javascript_bound_callable(result, module_name: str) -> None:
    qnames = _node_qnames(result, "callable")
    assert f"{module_name}.build" in qnames
    assert f"{module_name}.Widget.field" in qnames


def _assert_javascript_local_inheritance(result, module_name: str) -> None:
    edges = _edge_tuples(result)
    assert (f"{module_name}.Child", "EXTENDS", f"{module_name}.Base") in edges
    assert (f"{module_name}.Local", "EXTENDS", f"{module_name}.Base") in edges


_SCENARIOS: dict[tuple[str, str], tuple[str, str, object]] = {
    ("python", "class_declaration"): (
        "pkg/mod.py",
        """
class Widget:
    pass
""",
        _assert_python_class_declaration,
    ),
    ("python", "function_declaration"): (
        "pkg/mod.py",
        """
async def run():
    return 1
""",
        _assert_python_function_declaration,
    ),
    ("python", "bound_callable_declaration"): (
        "pkg/mod.py",
        """
build = lambda: 1
""",
        _assert_python_bound_callable,
    ),
    ("python", "decorated_definition_unwrap"): (
        "pkg/mod.py",
        """
def marker(fn):
    return fn

@marker
def decorated():
    return 1
""",
        _assert_python_decorated_definition,
    ),
    ("python", "local_inheritance_edges"): (
        "pkg/mod.py",
        """
class Base:
    pass

class Child(Base):
    pass
""",
        _assert_python_local_inheritance,
    ),
    ("typescript", "class_like_declaration"): (
        "src/mod.ts",
        """
export interface Shape {
  check(): void;
}

export abstract class Base {}
export class Child extends Base implements Shape {
  check() {}
}
""",
        _assert_typescript_class_like,
    ),
    ("typescript", "callable_declaration"): (
        "src/mod.ts",
        """
export interface Shape {
  check(): void;
}

export abstract class Base {
  abstract load(): void;
}

export class Child {
  work() {}
}

export function run() {}
""",
        _assert_typescript_callable_declaration,
    ),
    ("typescript", "class_and_function_expressions"): (
        "src/mod.ts",
        """
export const helper = () => 1;
const make = function () { return helper(); };
const Factory = class {
  run() { return make(); }
};
""",
        _assert_typescript_expression_constructs,
    ),
    ("typescript", "instance_and_alias_tracking"): (
        "src/mod.ts",
        """
class Service {
  run() {}
}

export function handle() {
  const svc = new Service();
  svc.run();
}
""",
        _assert_typescript_instance_tracking,
    ),
    ("typescript", "local_inheritance_edges"): (
        "src/mod.ts",
        """
interface Role {}
class Base {}
class Child extends Base implements Role {}
const Local = class extends Base {};
""",
        _assert_typescript_local_inheritance,
    ),
    ("java", "class_like_declaration"): (
        "src/Shape.java",
        """
interface Role {}
enum Mode { ON }
record Point(int x) {}
class Base {}
""",
        _assert_java_class_like,
    ),
    ("java", "method_like_declaration"): (
        "src/Widget.java",
        """
class Widget {
  Widget() {}
  void run() {}
}

record Point(int x) {
  Point {}
}
""",
        _assert_java_method_like,
    ),
    ("java", "field_type_tracking"): (
        "src/Holder.java",
        """
class Service {
  void run() {}
}

class Holder {
  Service svc;
  void handle() {
    svc.run();
  }
}
""",
        _assert_java_field_tracking,
    ),
    ("java", "local_inheritance_edges"): (
        "src/Child.java",
        """
class Base {}
interface Role {}
class Child extends Base implements Role {}
""",
        _assert_java_local_inheritance,
    ),
    ("javascript", "class_declaration"): (
        "src/mod.js",
        """
class Base {}
const Local = class extends Base {};
""",
        _assert_javascript_class_declaration,
    ),
    ("javascript", "callable_declaration"): (
        "src/mod.js",
        """
export function run() {}
class Widget {
  handle() {}
}
""",
        _assert_javascript_callable_declaration,
    ),
    ("javascript", "bound_callable_declaration"): (
        "src/mod.js",
        """
const build = () => 1;
class Widget {
  field = () => build();
}
""",
        _assert_javascript_bound_callable,
    ),
    ("javascript", "local_inheritance_edges"): (
        "src/mod.js",
        """
class Base {}
class Child extends Base {}
const Local = class extends Base {};
""",
        _assert_javascript_local_inheritance,
    ),
}


def test_canonical_surface_scenarios_cover_all_declared_constructs() -> None:
    declared = {
        (language, entry["construct"])
        for language, entries in build_walker_capabilities().items()
        for entry in entries
    }
    assert set(_SCENARIOS) == declared


@pytest.mark.parametrize(
    ("language", "construct"),
    sorted(_SCENARIOS),
)
def test_declared_constructs_have_canonical_black_box_fixture(
    tmp_path: Path,
    language: str,
    construct: str,
) -> None:
    relative_path, source, check = _SCENARIOS[(language, construct)]
    analyzer = _analyzer_for(language)
    snapshot = _snapshot(tmp_path, relative_path, language, source)
    module_name = analyzer.module_name(tmp_path, snapshot)
    analyzer.module_index = {module_name}
    result = analyzer.analyze(snapshot, module_name)
    check(result, module_name)
