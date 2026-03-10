# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.data_storage.core_db import connect as db_connect
from sciona.runtime.common import constants as setup_config
from sciona.runtime.paths import get_db_path


def test_connect_enables_wal(tmp_path):
    repo_root = tmp_path
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    sciona_dir.mkdir()

    conn = db_connect(get_db_path(repo_root), repo_root=repo_root)
    try:
        row = conn.execute("PRAGMA journal_mode").fetchone()
    finally:
        conn.close()

    assert row[0].lower() == "wal"


def test_connect_handles_repo_paths_with_uri_special_characters(tmp_path):
    repo_root = tmp_path / "repo?frag"
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    sciona_dir.mkdir(parents=True)

    conn = db_connect(get_db_path(repo_root), repo_root=repo_root)
    try:
        row = conn.execute("PRAGMA journal_mode").fetchone()
    finally:
        conn.close()

    assert row[0].lower() == "wal"
