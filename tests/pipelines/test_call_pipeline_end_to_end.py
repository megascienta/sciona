# SPDX-License-Identifier: MIT

from __future__ import annotations

import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import rollups
from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.core.extract.calls import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.pipelines.ops import repo as repo_pipeline
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import seed_repo_with_snapshot


def test_call_pipeline_end_to_end_filters_persists_and_reports(tmp_path: Path) -> None:
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
            artifact_conn.commit()
            node_call_rows = artifact_conn.execute(
                """
                SELECT callee_id
                FROM node_calls
                WHERE caller_id = ?
                ORDER BY callee_id
                """,
                ("meth_alpha",),
            ).fetchall()
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()

    assert [row["callee_id"] for row in node_call_rows] == ["func_alpha"]

    payload = repo_pipeline.snapshot_report(
        snapshot_id,
        repo_root=repo_root,
        include_failure_reasons=True,
    )
    assert payload is not None
    python = payload["languages"]["python"]
    assert python["call_materialization"] == {
        "finalized_call_edges": 1,
    }


def test_call_pipeline_reports_pair_centric_counts_for_persisted_dropped_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            set(),
            set(),
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {},
                "dropped_by_reason": {"ambiguous_no_in_scope_candidate": 1},
                "candidate_count_histogram": {3: 1},
            },
                [
                    (
                        "vendor.external.unknownfn",
                        "dropped",
                        None,
                        None,
                    "ambiguous_no_in_scope_candidate",
                    3,
                    "qualified",
                    None,
                    None,
                    1,
                    0,
                    "vendor.external",
                ),
            ],
        )

    monkeypatch.setattr(rollups, "_resolve_callees", _fake_resolve_callees)
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
                        callee_identifiers=("vendor.external.unknownfn",),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            artifact_conn.commit()
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()

    payload = repo_pipeline.snapshot_report(
        snapshot_id,
        repo_root=repo_root,
        include_failure_reasons=True,
    )
    assert payload is not None
    python = payload["languages"]["python"]
    assert python["call_materialization"] == {
        "finalized_call_edges": 0,
    }
