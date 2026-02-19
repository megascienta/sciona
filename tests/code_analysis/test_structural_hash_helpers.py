# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

from sciona.code_analysis.analysis.structural_hash import compute_structural_hash
from tests.helpers import seed_repo_with_snapshot


def test_compute_structural_hash_is_stable(tmp_path) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    first = compute_structural_hash(conn, snapshot_id)
    second = compute_structural_hash(conn, snapshot_id)
    conn.close()

    assert first == second
    assert len(first) == 64
