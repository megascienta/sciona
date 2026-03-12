# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.data_storage.common.transactions import transaction
from sciona.runtime.paths import get_artifact_db_path


def _artifact_db_conn(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    return conn, repo_root


def test_node_calls_and_cleanup(tmp_path: Path):
    conn, _ = _artifact_db_conn(tmp_path)
    try:
        with transaction(conn):
            artifact_write.upsert_node_calls(
                conn,
                caller_id="node-alpha",
                callee_ids=["node-beta", "node-gamma"],
                valid=True,
                call_hash="hash-alpha",
            )
        rows = conn.execute(
            "SELECT caller_id, callee_id FROM node_calls ORDER BY callee_id"
        ).fetchall()
        assert [(row["caller_id"], row["callee_id"]) for row in rows] == [
            ("node-alpha", "node-beta"),
            ("node-alpha", "node-gamma"),
        ]

        with transaction(conn):
            artifact_write.cleanup_removed_nodes(conn, {"node-alpha", "node-beta"})
        remaining = conn.execute(
            "SELECT caller_id, callee_id FROM node_calls ORDER BY callee_id"
        ).fetchall()
        assert [(row["caller_id"], row["callee_id"]) for row in remaining] == [
            ("node-alpha", "node-beta")
        ]
    finally:
        conn.close()


def test_artifact_db_creates_covering_call_sites_index(tmp_path: Path):
    conn, _ = _artifact_db_conn(tmp_path)
    try:
        rows = conn.execute("PRAGMA index_list(call_sites)").fetchall()
    finally:
        conn.close()

    index_names = {row["name"] for row in rows}
    assert "idx_call_sites_caller_status_callee" in index_names


def test_artifact_db_creates_callsite_pairs_indexes(tmp_path: Path):
    conn, _ = _artifact_db_conn(tmp_path)
    try:
        rows = conn.execute("PRAGMA index_list(callsite_pairs)").fetchall()
    finally:
        conn.close()

    index_names = {row["name"] for row in rows}
    assert "idx_callsite_pairs_caller" in index_names
    assert "idx_callsite_pairs_callee" in index_names


def test_callsite_pairs_write_and_cleanup(tmp_path: Path):
    conn, _ = _artifact_db_conn(tmp_path)
    try:
        with transaction(conn):
            artifact_write.upsert_callsite_pairs(
                conn,
                snapshot_id="snap-1",
                caller_id="node-alpha",
                rows=(
                    ("helper", "site-1", "node-beta", "in_repo_candidate"),
                    ("helper", "site-2", "node-gamma", "in_repo_candidate"),
                ),
            )
        rows = conn.execute(
            """
            SELECT snapshot_id, caller_id, identifier, site_hash, callee_id, pair_kind
            FROM callsite_pairs
            ORDER BY callee_id
            """
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            (
                "snap-1",
                "node-alpha",
                "helper",
                "site-1",
                "node-beta",
                "in_repo_candidate",
            ),
            (
                "snap-1",
                "node-alpha",
                "helper",
                "site-2",
                "node-gamma",
                "in_repo_candidate",
            ),
        ]

        with transaction(conn):
            artifact_write.cleanup_removed_nodes(conn, {"node-alpha", "node-beta"})
        remaining = conn.execute(
            "SELECT caller_id, callee_id FROM callsite_pairs ORDER BY callee_id"
        ).fetchall()
        assert [tuple(row) for row in remaining] == [("node-alpha", "node-beta")]
    finally:
        conn.close()
