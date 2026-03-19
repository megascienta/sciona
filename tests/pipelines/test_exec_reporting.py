# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import pytest

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.data_storage.artifact_db.maintenance import rebuild_graph_index
from sciona.pipelines.exec import reporting as exec_reporting
from sciona.pipelines.ops import repo as repo_pipeline
from sciona.runtime.common import constants as runtime_constants
from tests.helpers import core_conn as open_core_conn


def test_snapshot_report_returns_grouped_direct_metrics(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["labels"]["sections"]["structure"] == "Structure"
    assert payload["labels"]["scopes"] == {
        "non_tests": "Non-Tests",
        "tests": "Tests",
    }
    assert payload["timing"] == {
        "build_total_seconds": None,
        "build_wall_seconds": None,
        "build_phase_timings": {},
    }
    assert payload["totals"]["structure"] == {
        "files": 3,
        "nodes": 5,
        "edges": 5,
    }
    assert payload["totals"]["callsites"] == {
        "observed_syntactic_callsites": 0,
        "accepted_callsites": 0,
        "not_accepted_callsites": 0,
    }
    assert payload["totals"]["call_materialization"] == {
        "finalized_call_edges": 0,
    }
    assert payload["scopes"] == {
        "non_tests": {
            "structure": {
                "files": 3,
                "nodes": 5,
                "edges": 5,
            },
            "callsites": {
                "observed_syntactic_callsites": 0,
                "accepted_callsites": 0,
                "not_accepted_callsites": 0,
            },
            "call_materialization": {
                "finalized_call_edges": 0,
            },
        },
        "tests": {
            "structure": {
                "files": 0,
                "nodes": 0,
                "edges": 0,
            },
            "callsites": {
                "observed_syntactic_callsites": 0,
                "accepted_callsites": 0,
                "not_accepted_callsites": 0,
            },
            "call_materialization": {
                "finalized_call_edges": 0,
            },
        },
    }
    python = payload["languages"]["python"]
    assert python["structure"] == {"files": 3, "nodes": 5, "edges": 5}
    assert python["callsites"] == {
        "observed_syntactic_callsites": 0,
        "accepted_callsites": 0,
        "not_accepted_callsites": 0,
    }
    assert python["call_materialization"] == {
        "finalized_call_edges": 0,
    }


def test_snapshot_report_includes_timing_under_timing_group(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_total_seconds:{snapshot_id}",
            value="3.250000",
        )
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_wall_seconds:{snapshot_id}",
            value="4.500000",
        )
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_phase_timings:{snapshot_id}",
            value='{"discover_files": 0.12, "build_structural_index": 2.75, "prepare_durable_calls": 0.50, "write_durable_calls": 0.10}',
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["timing"]["build_total_seconds"] == pytest.approx(3.25)
    assert payload["timing"]["build_wall_seconds"] == pytest.approx(4.5)
    assert payload["timing"]["build_phase_timings"] == {
        "discover_files": pytest.approx(0.12),
        "build_structural_index": pytest.approx(2.75),
        "prepare_durable_calls": pytest.approx(0.50),
        "write_durable_calls": pytest.approx(0.10),
    }


def test_snapshot_report_includes_direct_callsite_counts_from_diagnostics(
    repo_with_snapshot,
):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"call_resolution_diagnostics:{snapshot_id}",
            value=(
                '{"totals": {"observed_callsites": 5, "filtered_before_persist": 2, '
                '"persisted_callsites": 3, "finalized_accepted_callsites": 2, '
                '"finalized_dropped_callsites": 1, '
                '"filtered_pre_persist_buckets": {"no_in_repo_candidate": 2}}, '
                '"by_caller": {"meth_alpha": {"observed_callsites": 5, '
                '"filtered_before_persist": 2, "persisted_callsites": 3, '
                '"finalized_accepted_callsites": 2, "finalized_dropped_callsites": 1, '
                '"filtered_pre_persist_buckets": {"no_in_repo_candidate": 2}}}}'
            ),
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["totals"]["callsites"] == {
        "observed_syntactic_callsites": 5,
        "accepted_callsites": 2,
        "not_accepted_callsites": 3,
    }
    assert payload["totals"]["call_materialization"] == {
        "finalized_call_edges": 0,
    }
    assert payload["totals"]["structure"]["edges"] == 5
    assert payload["scopes"]["non_tests"]["callsites"] == {
        "observed_syntactic_callsites": 5,
        "accepted_callsites": 2,
        "not_accepted_callsites": 3,
    }
    assert payload["scopes"]["non_tests"]["structure"] == {
        "files": 3,
        "nodes": 5,
        "edges": 5,
    }
    python = payload["languages"]["python"]
    assert python["callsites"]["accepted_callsites"] == 2


def test_snapshot_report_counts_finalized_call_edges(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    core_db = open_core_conn(repo_root)
    try:
        artifact_write.upsert_node_calls(
            conn,
            caller_id="meth_alpha",
            callee_ids=("func_alpha", "meth_alpha"),
            call_hash="hash-meth-alpha",
        )
        rebuild_graph_index(conn, core_conn=core_db, snapshot_id=snapshot_id)
        conn.commit()
    finally:
        conn.close()
        core_db.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    python = payload["languages"]["python"]
    assert python["structure"] == {"files": 3, "nodes": 5, "edges": 7}
    assert python["call_materialization"] == {
        "finalized_call_edges": 2,
    }
    assert payload["totals"]["structure"] == {"files": 3, "nodes": 5, "edges": 7}
    assert payload["totals"]["call_materialization"] == {
        "finalized_call_edges": 2,
    }
    assert payload["scopes"]["non_tests"]["structure"] == {
        "files": 3,
        "nodes": 5,
        "edges": 7,
    }
    assert payload["scopes"]["non_tests"]["call_materialization"] == {
        "finalized_call_edges": 2,
    }


def test_snapshot_report_attributes_graph_edges_by_source_scope(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    core_db = open_core_conn(repo_root)
    artifact_conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        core_db.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("mod_test", "module", "python", snapshot_id),
        )
        core_db.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_test", "callable", "python", snapshot_id),
        )
        core_db.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:mod_test",
                "mod_test",
                snapshot_id,
                "repo.tests.test_api",
                "tests/test_api.py",
                1,
                10,
                "hash-mod-test",
            ),
        )
        core_db.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_test",
                "func_test",
                snapshot_id,
                "repo.tests.test_api.test_helper",
                "tests/test_api.py",
                1,
                10,
                "hash-func-test",
            ),
        )
        core_db.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_test", "func_test", "LEXICALLY_CONTAINS"),
        )
        core_db.commit()

        artifact_write.upsert_node_calls(
            artifact_conn,
            caller_id="func_test",
            callee_ids=("func_alpha",),
            call_hash="hash-func-test",
        )
        rebuild_graph_index(artifact_conn, core_conn=core_db, snapshot_id=snapshot_id)
        artifact_conn.commit()
    finally:
        artifact_conn.close()
        core_db.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["totals"]["structure"] == {"files": 4, "nodes": 7, "edges": 7}
    assert payload["scopes"]["non_tests"]["structure"] == {
        "files": 3,
        "nodes": 5,
        "edges": 5,
    }
    assert payload["scopes"]["tests"]["structure"] == {
        "files": 1,
        "nodes": 2,
        "edges": 2,
    }
    assert payload["scopes"]["tests"]["call_materialization"] == {
        "finalized_call_edges": 1,
    }


def test_scope_bucket_detects_test_and_non_test_paths() -> None:
    assert exec_reporting._scope_bucket("pkg/service.py") == "non_tests"
    assert exec_reporting._scope_bucket("tests/test_api.py") == "tests"
    assert exec_reporting._scope_bucket("src/test/java/org/example/AppTest.java") == "tests"
