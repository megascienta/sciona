from __future__ import annotations

import sqlite3
from pathlib import Path

from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.maintenance_graph import rebuild_graph_index
from sciona.data_storage.transactions import transaction
from sciona.runtime.paths import get_artifact_db_path
from sciona.pipelines.domain.artifacts import rebuild_graph_rollups, write_call_artifacts

from .helpers import seed_repo_with_snapshot


def test_rollups_use_structural_ids_for_module_edges(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        call_records = [
            CallExtractionRecord(
                caller_structural_id="meth_alpha",
                caller_qualified_name="pkg.alpha.Service.run",
                caller_node_type="method",
                callee_identifiers=("helper",),
            )
        ]
        with transaction(artifact_conn):
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers={"meth_alpha"},
            )
            rebuild_graph_index(artifact_conn, core_conn=core_conn, snapshot_id=snapshot_id)
            rebuild_graph_rollups(artifact_conn, core_conn=core_conn, snapshot_id=snapshot_id)

        rows = artifact_conn.execute(
            "SELECT src_module_id, dst_module_id, call_count FROM module_call_edges"
        ).fetchall()
        assert rows
        assert rows[0]["src_module_id"] == "mod_alpha"
        assert rows[0]["dst_module_id"] == "mod_alpha"
        assert int(rows[0]["call_count"]) >= 1
    finally:
        artifact_conn.close()
        core_conn.close()
