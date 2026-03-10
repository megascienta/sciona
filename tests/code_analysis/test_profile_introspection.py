# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.tools.profiling import (
    java_class_extras,
    java_function_extras,
    javascript_class_extras,
    javascript_function_extras,
    python_class_extras,
    python_function_extras,
    typescript_class_extras,
    typescript_function_extras,
)
from sciona.code_analysis.tools.profiling.cache import (
    _javascript_inspector_cached,
    _java_inspector_cached,
    _python_inspector_cached,
    _typescript_inspector_cached,
)
from sciona.code_analysis.tools.profiling.typescript import (
    _TypeScriptInspector,
    _fuzzy_span_lookup,
)
from sciona.code_analysis.tools.profiling.query_surface import (
    JAVA_PROFILE_CLASS_NODE_TYPES,
    JAVA_PROFILE_FUNCTION_NODE_TYPES,
    JAVA_PROFILE_PARAMETER_NODE_TYPES,
    TYPESCRIPT_PROFILE_CLASS_NODE_TYPES,
)


def test_java_profile_parameter_surface_excludes_spread_parameter() -> None:
    assert "spread_parameter" not in JAVA_PROFILE_PARAMETER_NODE_TYPES


def test_profile_surfaces_include_parity_nodes() -> None:
    assert "compact_constructor_declaration" in JAVA_PROFILE_FUNCTION_NODE_TYPES
    assert "interface_declaration" in JAVA_PROFILE_CLASS_NODE_TYPES
    assert "enum_declaration" in JAVA_PROFILE_CLASS_NODE_TYPES
    assert "record_declaration" in JAVA_PROFILE_CLASS_NODE_TYPES
    assert "abstract_class_declaration" in TYPESCRIPT_PROFILE_CLASS_NODE_TYPES
    assert "class_expression" in TYPESCRIPT_PROFILE_CLASS_NODE_TYPES


def test_python_introspection_extras(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    file_path = repo_root / "pkg" / "mod.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(
        """
@decorator
class Widget(Base):
    def method(self, a, *, b=False, **kw):
        return a

@decorator
def helper(x, *args, **kwargs):
    return x
""".lstrip(),
        encoding="utf-8",
    )
    bases = python_class_extras(
        "python",
        repo_root,
        "pkg/mod.py",
        start_line=2,
        end_line=4,
    )
    assert bases == ["Base"]

    params = python_function_extras(
        "python",
        repo_root,
        "pkg/mod.py",
        start_line=7,
        end_line=8,
    )
    assert params == ["x", "*args", "**kwargs"]


def test_typescript_introspection_extras(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    file_path = repo_root / "pkg" / "mod.ts"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(
        """
@sealed
export class Widget extends Base {
  public run(userId: string, force?: boolean) {
    return userId;
  }
}

export function makeWidget(name: string, ...args: string[]) {
  return name;
}
""".lstrip(),
        encoding="utf-8",
    )
    bases = typescript_class_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=2,
        end_line=6,
    )
    if bases:
        assert bases == ["Base"]

    params = typescript_function_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=8,
        end_line=10,
    )
    assert "name" in params
    assert "...args" in params


def test_typescript_introspection_expression_extras(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    file_path = repo_root / "pkg" / "mod.ts"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(
        """
class Base {}
const build = (name: string) => name;
class Holder {
  runner = (arg: string) => arg;
}
const Local = class extends Base {};
""".lstrip(),
        encoding="utf-8",
    )
    params = typescript_function_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=2,
        end_line=2,
    )
    assert params == ["name"]
    member_params = typescript_function_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=4,
        end_line=4,
    )
    assert member_params == ["arg"]
    class_bases = typescript_class_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=6,
        end_line=6,
    )
    assert class_bases == []
    inspector = _TypeScriptInspector(file_path.read_text(encoding="utf-8"))
    assert (6, 6) in inspector.classes


def test_javascript_introspection_extras(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    file_path = repo_root / "pkg" / "mod.js"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(
        """
class Base {}
class Widget extends Base {
  run(userId, retries) {
    return userId + retries;
  }
}
""".lstrip(),
        encoding="utf-8",
    )
    bases = javascript_class_extras(
        "javascript",
        repo_root,
        "pkg/mod.js",
        start_line=2,
        end_line=6,
    )
    assert "Base" in bases

    params = javascript_function_extras(
        "javascript",
        repo_root,
        "pkg/mod.js",
        start_line=3,
        end_line=5,
    )
    assert params == ["userId", "retries"]


def test_java_introspection_extras(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    file_path = repo_root / "pkg" / "Mod.java"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(
        """
package pkg;
class Base {}
interface Role {}
@Entity
class Widget extends Base implements Role {
  Widget() {}
  @Timed
  void run(String userId, int retries) {}
}
""".lstrip(),
        encoding="utf-8",
    )
    bases = java_class_extras(
        "java",
        repo_root,
        "pkg/Mod.java",
        start_line=4,
        end_line=9,
    )
    assert "Base" in bases
    assert "Role" in bases

    params = java_function_extras(
        "java",
        repo_root,
        "pkg/Mod.java",
        start_line=7,
        end_line=8,
    )
    assert params == ["userId", "retries"]


def test_typescript_fuzzy_span_lookup_prefers_closest_covering_end_line() -> None:
    index = {
        10: [
            ((10, 22), "late"),
            ((10, 12), "covering"),
            ((10, 8), "short"),
        ]
    }
    assert _fuzzy_span_lookup(index, 10, 11) == "covering"
    assert _fuzzy_span_lookup(index, 10, 30) == "late"


def test_profile_inspector_loaders_are_memoized(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pkg").mkdir()
    (repo_root / "pkg" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (repo_root / "pkg" / "a.ts").write_text("class A {}\n", encoding="utf-8")
    (repo_root / "pkg" / "a.js").write_text("class A {}\n", encoding="utf-8")
    (repo_root / "pkg" / "A.java").write_text("class A {}\n", encoding="utf-8")

    root_key = str(repo_root.resolve())
    _python_inspector_cached.cache_clear()
    _typescript_inspector_cached.cache_clear()
    _javascript_inspector_cached.cache_clear()
    _java_inspector_cached.cache_clear()

    py_first = _python_inspector_cached(root_key, "pkg/a.py")
    py_second = _python_inspector_cached(root_key, "pkg/a.py")
    assert py_first is py_second

    ts_first = _typescript_inspector_cached(root_key, "pkg/a.ts")
    ts_second = _typescript_inspector_cached(root_key, "pkg/a.ts")
    assert ts_first is ts_second

    js_first = _javascript_inspector_cached(root_key, "pkg/a.js")
    js_second = _javascript_inspector_cached(root_key, "pkg/a.js")
    assert js_first is js_second

    java_first = _java_inspector_cached(root_key, "pkg/A.java")
    java_second = _java_inspector_cached(root_key, "pkg/A.java")
    assert java_first is java_second


def test_profile_inspector_loaders_reject_absolute_and_traversing_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pkg").mkdir()
    (repo_root / "pkg" / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    outside = tmp_path / "secret.py"
    outside.write_text("print('secret')\n", encoding="utf-8")

    root_key = str(repo_root.resolve())
    _python_inspector_cached.cache_clear()

    assert _python_inspector_cached(root_key, str(outside)) is None
    assert _python_inspector_cached(root_key, "../secret.py") is None
