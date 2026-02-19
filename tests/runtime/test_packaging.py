# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.runtime.packaging import local_package_names


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
