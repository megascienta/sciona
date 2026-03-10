# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path
import pytest

from sciona.code_analysis.core.normalize_model import FileRecord, FileSnapshot
from sciona.code_analysis.tools.snapshots import count_lines_fast, prepare_file_snapshots
from tests.helpers import init_git_repo, commit_all


def test_count_lines_fast_counts_lines(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("a\nb\n", encoding="utf-8")
    assert count_lines_fast(file_path) == 2


def test_prepare_file_snapshots_uses_git_blob(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    file_path = repo_root / "pkg" / "mod.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("print('hi')\n", encoding="utf-8")
    commit_all(repo_root)

    record = FileRecord(
        path=file_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    snapshots = prepare_file_snapshots(repo_root, [record])
    assert len(snapshots) == 1
    assert snapshots[0].blob_sha
    assert snapshots[0].line_count == 1


def test_prepare_file_snapshots_rejects_symlink_target_outside_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)

    outside = tmp_path / "secret.py"
    outside.write_text("print('secret')\n", encoding="utf-8")
    link_path = repo_root / "pkg" / "mod.py"
    link_path.parent.mkdir(parents=True)
    link_path.symlink_to(outside)
    commit_all(repo_root)

    record = FileRecord(
        path=link_path,
        relative_path=Path("pkg/mod.py"),
        language="python",
    )
    with pytest.raises(ValueError):
        prepare_file_snapshots(repo_root, [record])


def test_file_snapshot_content_rejects_path_outside_derived_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "secret.py"
    outside.write_text("print('secret')\n", encoding="utf-8")
    snapshot = FileSnapshot(
        record=FileRecord(
            path=outside,
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="file",
        blob_sha="hash",
        size=outside.stat().st_size,
        line_count=1,
        content=None,
    )
    with pytest.raises(ValueError):
        _ = snapshot.content
