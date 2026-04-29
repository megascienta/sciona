# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.packaging import local_package_module_roots, local_package_names


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
