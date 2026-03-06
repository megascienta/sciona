# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from tests.helpers import core_conn, parse_json_payload, seed_repo_with_snapshot
from sciona.reducers import hotspot_summary


def test_hotspot_summary_includes_counts(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload = hotspot_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    data = parse_json_payload(payload)
    for key in ("by_fan_in", "by_fan_out", "by_size"):
        entries = data.get(key) or []
        assert entries, f"{key} should not be empty"
        for entry in entries:
            assert isinstance(entry.get("module_qualified_name"), str)
            assert isinstance(entry.get("count"), int)
