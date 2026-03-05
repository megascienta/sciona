# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

import yaml

from sciona.pipelines.exec import init_dialog
from sciona.runtime import constants as setup_config
from tests.helpers import init_git_repo, commit_all


def _write_config(repo_root: Path) -> Path:
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    sciona_dir.mkdir(exist_ok=True)
    config_path = sciona_dir / "config.yaml"
    config_path.write_text(
        """languages:\n  python:\n    enabled: false\n  typescript:\n    enabled: false\n  javascript:\n    enabled: false\n\ndiscovery:\n  exclude_globs: []\n""",
        encoding="utf-8",
    )
    return config_path


def test_supported_languages_sorted() -> None:
    langs = init_dialog.supported_languages()
    assert langs == sorted(langs)
    assert "python" in langs
    assert "javascript" in langs
    assert "fortran" in langs


def test_installed_and_missing_languages_surfaces() -> None:
    installed = init_dialog.installed_languages()
    missing = init_dialog.missing_languages()
    assert "python" in installed
    assert "javascript" in installed
    assert "fortran" in missing


def test_apply_language_selection_updates_config(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    config_path = _write_config(repo_root)
    init_dialog.apply_language_selection(repo_root, ["python", "javascript"])
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert data["languages"]["python"]["enabled"] is True
    assert data["languages"]["javascript"]["enabled"] is True


def test_detect_languages_from_tracked_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    (repo_root / "pkg").mkdir()
    (repo_root / "pkg" / "mod.py").write_text("print('hi')\n", encoding="utf-8")
    (repo_root / "pkg" / "mod.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (repo_root / "pkg" / "mod.js").write_text("export const y = 2;\n", encoding="utf-8")
    commit_all(repo_root)

    defaults = init_dialog.detect_languages(repo_root)
    assert "python" in defaults.detected_languages
    assert "javascript" in defaults.detected_languages
    assert "python" in defaults.installed_languages
    assert "javascript" in defaults.installed_languages
    assert "fortran" in defaults.missing_languages
