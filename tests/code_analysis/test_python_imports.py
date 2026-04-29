# SPDX-License-Identifier: MIT

from sciona.code_analysis.languages.builtin.python.python_imports import normalize_import


def test_normalize_import_resolves_relative_single_dot() -> None:
    normalized = normalize_import(
        ".helpers",
        module_name="repo.pkg.mod",
        is_package=False,
        repo_prefix="repo",
        local_package_roots={"pkg": "pkg"},
    )
    assert normalized == "repo.pkg.helpers"


def test_normalize_import_resolves_relative_double_dot() -> None:
    normalized = normalize_import(
        "..utils",
        module_name="repo.pkg.sub.mod",
        is_package=False,
        repo_prefix="repo",
        local_package_roots={"pkg": "pkg"},
    )
    assert normalized == "repo.pkg.utils"


def test_normalize_import_rejects_relative_beyond_package_root() -> None:
    normalized = normalize_import(
        "..oops",
        module_name="repo",
        is_package=True,
        repo_prefix="repo",
        local_package_roots={"pkg": "pkg"},
    )
    assert normalized is None


def test_normalize_import_resolves_absolute_local_package_to_canonical_module() -> None:
    normalized = normalize_import(
        "pkg.core.errors",
        module_name="repo.src.pkg.api.app",
        is_package=False,
        repo_prefix="repo",
        local_package_roots={"pkg": "src.pkg"},
    )
    assert normalized == "repo.src.pkg.core.errors"
