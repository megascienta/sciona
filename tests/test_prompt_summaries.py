# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json
import sqlite3

from tests.helpers import seed_repo_with_snapshot
from sciona.reducers.summaries import hotspot_summary


def _parse_json_block(payload: str) -> dict:
    lines = payload.strip().splitlines()
    assert lines[0] == "```json"
    assert lines[-1] == "```"
    return json.loads("\n".join(lines[1:-1]))


def test_hotspot_summary_includes_counts(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    try:
        payload = hotspot_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    data = _parse_json_block(payload)
    for key in ("by_fan_in", "by_fan_out", "by_size"):
        entries = data.get(key) or []
        assert entries, f"{key} should not be empty"
        for entry in entries:
            assert isinstance(entry.get("module_qualified_name"), str)
            assert isinstance(entry.get("count"), int)
