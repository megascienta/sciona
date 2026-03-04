# SPDX-License-Identifier: MIT

from __future__ import annotations

import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import seed_repo_with_snapshot


def test_call_sites_persist_in_repo_candidates_only(tmp_path: Path) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
        try:
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=[
                    CallExtractionRecord(
                        caller_structural_id="meth_alpha",
                        caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
                        caller_node_type="callable",
                        callee_identifiers=("helper", "print"),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            rows = artifact_conn.execute(
                """
                SELECT identifier, resolution_status, candidate_count, callee_kind, call_ordinal
                FROM call_sites
                WHERE snapshot_id = ? AND caller_id = ?
                ORDER BY call_ordinal
                """,
                (snapshot_id, "meth_alpha"),
            ).fetchall()
            assert rows
            assert [row["identifier"] for row in rows] == ["helper"]
            assert rows[0]["resolution_status"] == "accepted"
            assert rows[0]["candidate_count"] > 0
            assert rows[0]["callee_kind"] == "terminal"
            assert rows[0]["call_ordinal"] == 1
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()
