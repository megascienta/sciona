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


def test_normalize_import_rewrites_package_colliding_with_repo_prefix() -> None:
    # Repo `gpumd-workflows` sanitizes to prefix `gpumd_workflows`, which is
    # also the src-layout package name; the package root rewrite must still
    # apply instead of passing the target through unchanged.
    normalized = normalize_import(
        "gpumd_workflows.io.gpumd",
        module_name="gpumd_workflows.src.gpumd_workflows.app.prepare_job",
        is_package=False,
        repo_prefix="gpumd_workflows",
        local_package_roots={"gpumd_workflows": "src.gpumd_workflows"},
    )
    assert normalized == "gpumd_workflows.src.gpumd_workflows.io.gpumd"


def test_normalize_import_rewrites_bare_package_colliding_with_repo_prefix() -> None:
    normalized = normalize_import(
        "gpumd_workflows",
        module_name="gpumd_workflows.src.gpumd_workflows.cli",
        is_package=False,
        repo_prefix="gpumd_workflows",
        local_package_roots={"gpumd_workflows": "src.gpumd_workflows"},
    )
    assert normalized == "gpumd_workflows.src.gpumd_workflows"
