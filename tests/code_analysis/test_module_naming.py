# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.code_analysis.languages.builtin import javascript as js_lang
from sciona.code_analysis.languages.builtin import python as python_lang
from sciona.code_analysis.languages.builtin import typescript as ts_lang
from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot


def _write_pyproject(repo_root: Path) -> None:
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[tool.setuptools.package-dir]",
                'sciona = "core"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def _snapshot_for(repo_root: Path, relative_path: Path, language: str) -> FileSnapshot:
    full_path = repo_root / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text("# test", encoding="utf-8")
    record = FileRecord(
        path=full_path,
        relative_path=relative_path,
        language=language,
    )
    return FileSnapshot(record=record, content=None)


def test_python_module_name_is_repo_relative_with_core_prefix(tmp_path):
    repo_root = tmp_path / "sciona"
    repo_root.mkdir()
    _write_pyproject(repo_root)
    snapshot = _snapshot_for(
        repo_root,
        Path("core/runtime/time.py"),
        "python",
    )
    assert python_lang.module_name(repo_root, snapshot) == "sciona.core.runtime.time"


def test_python_module_name_addons_prefix(tmp_path):
    repo_root = tmp_path / "sciona"
    repo_root.mkdir()
    _write_pyproject(repo_root)
    snapshot = _snapshot_for(
        repo_root,
        Path("addons/documentation/pipelines/artifacts.py"),
        "python",
    )
    assert (
        python_lang.module_name(repo_root, snapshot)
        == "sciona.addons.documentation.pipelines.artifacts"
    )


def test_python_module_name_core_addons_anchor(tmp_path):
    repo_root = tmp_path / "sciona"
    repo_root.mkdir()
    _write_pyproject(repo_root)
    snapshot = _snapshot_for(
        repo_root,
        Path("core/addons/__init__.py"),
        "python",
    )
    assert python_lang.module_name(repo_root, snapshot) == "sciona.core.addons"


def test_python_module_name_addons_anchor(tmp_path):
    repo_root = tmp_path / "sciona"
    repo_root.mkdir()
    _write_pyproject(repo_root)
    snapshot = _snapshot_for(
        repo_root,
        Path("addons/__init__.py"),
        "python",
    )
    assert python_lang.module_name(repo_root, snapshot) == "sciona.addons"


def test_typescript_module_name_includes_repo_prefix(tmp_path):
    repo_root = tmp_path / "sciona"
    repo_root.mkdir()
    snapshot = _snapshot_for(
        repo_root,
        Path("addons/documentation/assets/sample.ts"),
        "typescript",
    )
    assert (
        ts_lang.module_name(repo_root, snapshot)
        == "sciona.addons.documentation.assets.sample"
    )


def test_javascript_module_name_removes_js_suffix(tmp_path):
    repo_root = tmp_path / "sciona"
    repo_root.mkdir()
    snapshot = _snapshot_for(
        repo_root,
        Path("addons/documentation/assets/sample.js"),
        "javascript",
    )
    assert (
        js_lang.module_name(repo_root, snapshot)
        == "sciona.addons.documentation.assets.sample"
    )
