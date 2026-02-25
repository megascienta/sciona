# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.tools.profile_introspection import (
    java_class_extras,
    java_function_extras,
    python_class_extras,
    python_function_extras,
    typescript_class_extras,
    typescript_function_extras,
)


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
    decorators, bases = python_class_extras(
        "python",
        repo_root,
        "pkg/mod.py",
        start_line=2,
        end_line=4,
    )
    assert decorators == ["decorator"]
    assert bases == ["Base"]

    params, func_decorators = python_function_extras(
        "python",
        repo_root,
        "pkg/mod.py",
        start_line=7,
        end_line=8,
    )
    assert func_decorators == ["decorator"]
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
    decorators, bases = typescript_class_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=2,
        end_line=6,
    )
    if decorators:
        assert decorators == ["@sealed"]
    if bases:
        assert bases == ["Base"]

    params, func_decorators = typescript_function_extras(
        "typescript",
        repo_root,
        "pkg/mod.ts",
        start_line=8,
        end_line=10,
    )
    assert func_decorators == []
    assert "name" in params
    assert "...args" in params


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
    decorators, bases = java_class_extras(
        "java",
        repo_root,
        "pkg/Mod.java",
        start_line=4,
        end_line=9,
    )
    assert decorators == ["@Entity"]
    assert "Base" in bases
    assert "Role" in bases

    params, func_decorators = java_function_extras(
        "java",
        repo_root,
        "pkg/Mod.java",
        start_line=7,
        end_line=8,
    )
    assert func_decorators == ["@Timed"]
    assert params == ["userId", "retries"]
