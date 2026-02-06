# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

import pytest

from sciona.runtime import config as core_config
from sciona.code_analysis.tools import walker


def _settings(enabled: bool = True) -> dict[str, core_config.LanguageSettings]:
    return {
        "python": core_config.LanguageSettings(name="python", enabled=enabled),
        "typescript": core_config.LanguageSettings(name="typescript", enabled=False),
    }


def test_walker_tracks_paths_and_exclude_globs(tmp_path):
    repo = tmp_path
    (repo / "src").mkdir()
    kept = repo / "src" / "kept.py"
    kept.write_text("print('hi')\n", encoding="utf-8")
    skipped = repo / "src" / "dist" / "ignored.py"
    skipped.parent.mkdir()
    skipped.write_text("print('skip')\n", encoding="utf-8")

    discovery = core_config.DiscoverySettings(exclude_globs=["**/dist/**"])
    tracked = {Path("src/kept.py").as_posix(), Path("src/dist/ignored.py").as_posix()}
    records = walker.collect_files(
        repo, _settings(), discovery=discovery, tracked_paths=tracked
    )
    paths = [record.relative_path.as_posix() for record in records]
    assert paths == ["src/kept.py"]


def test_walker_hard_excludes_git_and_sciona(tmp_path):
    repo = tmp_path
    (repo / ".git").mkdir()
    (repo / ".sciona").mkdir()
    tracked = {
        Path(".git/ignored.py").as_posix(),
        Path(".sciona/ignored.py").as_posix(),
        Path("vendor/.git/hooks/ignored.py").as_posix(),
        Path("vendor/.sciona/ignored.py").as_posix(),
        Path("src/keep.py").as_posix(),
    }
    (repo / "vendor" / ".git" / "hooks").mkdir(parents=True)
    (repo / "vendor" / ".sciona").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "keep.py").write_text("print('ok')\n", encoding="utf-8")

    records = walker.collect_files(repo, _settings(), tracked_paths=tracked)
    paths = [record.relative_path.as_posix() for record in records]
    assert paths == ["src/keep.py"]


def test_walker_respects_enabled_languages_only(tmp_path):
    repo = tmp_path
    (repo / "src").mkdir()
    (repo / "src" / "mod.ts").write_text("export const x = 1;\n", encoding="utf-8")
    tracked = {Path("src/mod.ts").as_posix()}

    settings = {
        "python": core_config.LanguageSettings(name="python", enabled=True),
        "typescript": core_config.LanguageSettings(name="typescript", enabled=False),
    }
    records = walker.collect_files(repo, settings, tracked_paths=tracked)
    assert records == []


def test_walker_requires_tracked_paths(tmp_path):
    with pytest.raises(ValueError):
        walker.collect_files(tmp_path, _settings(), tracked_paths=None)


def test_walker_excludes_ignored_paths(tmp_path):
    repo = tmp_path
    (repo / "src").mkdir()
    (repo / "src" / "ignored.py").write_text("print('no')\n", encoding="utf-8")
    (repo / "src" / "kept.py").write_text("print('yes')\n", encoding="utf-8")
    tracked = {Path("src/ignored.py").as_posix(), Path("src/kept.py").as_posix()}
    ignored = {Path("src/ignored.py").as_posix()}

    records = walker.collect_files(
        repo, _settings(), tracked_paths=tracked, ignored_paths=ignored
    )
    paths = [record.relative_path.as_posix() for record in records]
    assert paths == ["src/kept.py"]
