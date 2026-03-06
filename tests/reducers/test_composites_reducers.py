# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.reducers import overlay_impact_summary
from sciona.runtime import constants as setup_config
from tests.helpers import core_conn, parse_json_payload, seed_repo_with_snapshot


def test_overlay_impact_summary_reports_unavailable_without_overlay(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = overlay_impact_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["overlay_advisory"] is True
    assert payload["overlay_available"] is False


def test_overlay_impact_summary_reads_latest_overlay_summary(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        conn.execute(
            """
            INSERT INTO diff_overlay_summary(snapshot_id, worktree_hash, summary_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                snapshot_id,
                "hash_new",
                json.dumps({"nodes": {"total": {"add": 1, "modify": 0, "remove": 0}}}),
                "2026-03-05T12:30:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO diff_overlay(snapshot_id, worktree_hash, structural_id, node_type, diff_kind, field, old_value, new_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                "hash_new",
                "func_alpha",
                "callable",
                "modify",
                "content_hash",
                "old",
                "new",
                "2026-03-05T12:30:00Z",
            ),
        )
        conn.execute(
            """
            INSERT INTO diff_overlay_calls(
                snapshot_id,
                worktree_hash,
                src_structural_id,
                dst_structural_id,
                diff_kind,
                src_node_type,
                dst_node_type,
                src_qualified_name,
                dst_qualified_name,
                src_file_path,
                dst_file_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                "hash_new",
                "func_alpha",
                "meth_alpha",
                "add",
                "callable",
                "callable",
                "pkg.alpha.service.helper",
                "pkg.alpha.Service.run",
                "pkg/alpha/service.py",
                "pkg/alpha/service.py",
                "2026-03-05T12:30:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    core = core_conn(repo_root)
    try:
        payload_text = overlay_impact_summary.render(snapshot_id, core, repo_root)
    finally:
        core.close()
    payload = parse_json_payload(payload_text)
    assert payload["overlay_advisory"] is True
    assert payload["overlay_available"] is True
    assert payload["worktree_hash"] == "hash_new"
    assert payload["node_change_count"] == 1
    assert payload["call_change_count"] == 1
