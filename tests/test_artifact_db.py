from pathlib import Path

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db import store as artifact_store
from sciona.data_storage.transactions import transaction
from sciona.pipelines.config import public as config


def _artifact_db_conn(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir()
    conn = artifact_connect(config.get_artifact_db_path(repo_root), repo_root=repo_root)
    return conn, repo_root


def test_node_status_rewrite_and_update(tmp_path: Path):
    conn, _ = _artifact_db_conn(tmp_path)
    try:
        with transaction(conn):
            artifact_store.rewrite_node_status(
                conn,
                statuses=[("alpha", "added"), ("beta", "modified")],
                producer_id=artifact_store.NODE_STATUS_PRODUCER,
            )
        statuses = artifact_store.get_node_status(conn)
        assert statuses == {"alpha": "added", "beta": "modified"}

        with transaction(conn):
            artifact_store.set_node_status(conn, "beta", "valid")
        assert artifact_store.get_node_status(conn)["beta"] == "valid"
    finally:
        conn.close()


def test_node_calls_and_cleanup(tmp_path: Path):
    conn, _ = _artifact_db_conn(tmp_path)
    try:
        with transaction(conn):
            artifact_store.upsert_node_calls(
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
            artifact_store.cleanup_removed_nodes(conn, {"node-alpha", "node-beta"})
        remaining = conn.execute(
            "SELECT caller_id, callee_id FROM node_calls ORDER BY callee_id"
        ).fetchall()
        assert [(row["caller_id"], row["callee_id"]) for row in remaining] == [
            ("node-alpha", "node-beta")
        ]
    finally:
        conn.close()
