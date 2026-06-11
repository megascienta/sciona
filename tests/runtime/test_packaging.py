# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.languages.builtin.python.python_packaging import (
    local_package_module_roots,
    local_package_names,
)


def test_local_package_names_empty_without_pyproject(tmp_path) -> None:
    assert local_package_names(tmp_path) == ()


def test_local_package_names_from_pyproject(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.setuptools.package-dir]
sciona = "src"
extras = "lib"
""",
        encoding="utf-8",
    )
    assert local_package_names(tmp_path) == ("extras", "sciona")


def test_local_package_names_from_setuptools_src_layout(tmp_path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.setuptools.package-dir]
"" = "src"

[tool.setuptools.packages.find]
where = ["src"]
""",
        encoding="utf-8",
    )
    src = tmp_path / "src"
    (src / "alpha").mkdir(parents=True)
    (src / "alpha" / "__init__.py").write_text("", encoding="utf-8")
    (src / "beta").mkdir(parents=True)
    (src / "beta" / "__init__.py").write_text("", encoding="utf-8")
    (src / "not_a_package").mkdir(parents=True)

    assert local_package_names(tmp_path) == ("alpha", "beta")
    assert local_package_module_roots(tmp_path) == {
        "alpha": "src.alpha",
        "beta": "src.beta",
    }


def test_local_package_module_roots_flat_layout_without_pyproject(tmp_path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "utils.py").write_text("", encoding="utf-8")

    assert local_package_module_roots(tmp_path) == {"pkg": "pkg"}
    assert local_package_names(tmp_path) == ("pkg",)


def test_local_package_module_roots_flat_layout_multiple_packages(tmp_path) -> None:
    for name in ("alpha", "beta"):
        pkg = tmp_path / name
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
    not_a_package = tmp_path / "not_a_package"
    not_a_package.mkdir()
    (not_a_package / "module.py").write_text("", encoding="utf-8")

    assert local_package_module_roots(tmp_path) == {"alpha": "alpha", "beta": "beta"}
    assert local_package_names(tmp_path) == ("alpha", "beta")


def test_local_package_module_roots_flat_layout_skipped_when_pyproject_present(
    tmp_path,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.setuptools.package-dir]
sciona = "src"
""",
        encoding="utf-8",
    )
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    assert local_package_module_roots(tmp_path) == {"sciona": "src"}


def test_local_package_module_roots_namespace_package_without_init(tmp_path) -> None:
    pkg = tmp_path / "pkg"
    sub = pkg / "sub"
    sub.mkdir(parents=True)
    (sub / "utils.py").write_text("", encoding="utf-8")
    hidden = tmp_path / ".cache"
    hidden.mkdir()
    (hidden / "ignored.py").write_text("", encoding="utf-8")

    assert local_package_module_roots(tmp_path) == {"pkg": "pkg"}


def test_local_package_module_roots_init_packages_shadow_namespace_dirs(tmp_path) -> None:
    init_pkg = tmp_path / "alpha"
    init_pkg.mkdir()
    (init_pkg / "__init__.py").write_text("", encoding="utf-8")
    namespace_pkg = tmp_path / "beta"
    namespace_pkg.mkdir()
    (namespace_pkg / "module.py").write_text("", encoding="utf-8")

    assert local_package_module_roots(tmp_path) == {"alpha": "alpha"}


def test_local_package_module_roots_empty_when_no_packages(tmp_path) -> None:
    (tmp_path / "module.py").write_text("", encoding="utf-8")

    assert local_package_module_roots(tmp_path) == {}
    assert local_package_names(tmp_path) == ()
