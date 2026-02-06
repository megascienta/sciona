import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.runtime.paths import get_artifact_db_path

from .helpers import seed_repo_with_snapshot


def test_write_call_artifacts_resolves_function(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    try:
        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
        try:
            statuses = {"meth_alpha": "added"}
            call_records = [
                CallExtractionRecord(
                    caller_structural_id="meth_alpha",
                    caller_qualified_name="pkg.alpha.Service.run",
                    caller_node_type="method",
                    callee_identifiers=("helper",),
                )
            ]
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers=set(statuses),
            )
            rows = artifact_conn.execute(
                "SELECT callee_id, valid FROM node_calls WHERE caller_id = ? ORDER BY callee_id",
                ("meth_alpha",),
            ).fetchall()
            assert rows
            assert rows[0][0] == "func_alpha"
            assert rows[0][1] == 1
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()
