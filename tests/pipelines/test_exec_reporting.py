# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import pytest

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.pipelines.ops import repo as repo_pipeline
from sciona.pipelines.exec import reporting as exec_reporting
from sciona.runtime.common import constants as runtime_constants


def test_snapshot_report_returns_pair_centric_counts(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["snapshot_id"] == snapshot_id
    assert (
        payload["callsite_pairs_semantics"]
        == "deduplicated_persisted_in_scope_candidate_pairs"
    )
    assert (
        payload["finalized_call_edges_semantics"]
        == "deduplicated_graph_edges_derived_from_callsite_pairs"
    )
    assert payload["totals"]["files"] == 3
    assert payload["totals"]["nodes"] == 5
    assert payload["totals"]["edges"] == 5
    assert payload["totals"]["callsite_pairs"] == {"count": 0}
    assert payload["totals"]["finalized_call_edges"] == {"count": 0}
    assert payload["totals"]["callsite_pairs_by_scope"]["non_tests"] == {"count": 0}
    assert payload["totals"]["callsite_pairs_by_scope"]["tests"] == {"count": 0}
    assert payload["totals"]["finalized_call_edges_by_scope"]["non_tests"] == {"count": 0}
    assert payload["totals"]["finalized_call_edges_by_scope"]["tests"] == {"count": 0}
    assert payload["totals"]["call_site_funnel"] == {
        "observed_syntactic_callsites": 0,
        "filtered_pre_persist": 0,
        "persisted_callsites": 0,
        "persisted_accepted": 0,
        "persisted_dropped": 0,
        "record_drops": {},
        "conservation_ok": True,
    }
    assert payload["totals"]["structural_density"]["files"] == 3
    assert payload["totals"]["structural_density"]["eligible_callsites"] == 0
    assert payload["totals"]["structural_density"]["inflation_warning"] is False
    python = {entry["language"]: entry for entry in payload["languages"]}["python"]
    assert python["callsite_pairs"] == {"count": 0}
    assert python["finalized_call_edges"] == {"count": 0}
    assert python["call_site_funnel"]["conservation_ok"] is True
    assert python["callsite_pairs_by_scope"]["non_tests"] == {"count": 0}
    assert python["callsite_pairs_by_scope"]["tests"] == {"count": 0}
    assert python["finalized_call_edges_by_scope"]["non_tests"] == {"count": 0}
    assert python["finalized_call_edges_by_scope"]["tests"] == {"count": 0}
    assert python["structural_density"]["eligible_callsites"] == 0


def test_snapshot_report_includes_build_total_seconds(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_total_seconds:{snapshot_id}",
            value="3.250000",
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["build_total_seconds"] == pytest.approx(3.25)


def test_snapshot_report_includes_wall_seconds_and_phase_timings(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_wall_seconds:{snapshot_id}",
            value="4.500000",
        )
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"build_phase_timings:{snapshot_id}",
            value='{"discover_files": 0.12, "build_structural_index": 2.75}',
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["build_wall_seconds"] == pytest.approx(4.5)
    assert payload["build_phase_timings"] == {
        "discover_files": pytest.approx(0.12),
        "build_structural_index": pytest.approx(2.75),
    }


def test_snapshot_report_includes_call_site_funnel_from_diagnostics(repo_with_snapshot):
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
                '"finalized_dropped_callsites": 1, "record_drops": {"no_resolved_callees": 1}, '
                '"filtered_pre_persist_buckets": {"zero_candidate_count": 2}}, '
                '"by_caller": {"meth_alpha": {"observed_callsites": 5, '
                '"filtered_before_persist": 2, "persisted_callsites": 3, '
                '"finalized_accepted_callsites": 2, "finalized_dropped_callsites": 1, '
                '"record_drops": {"no_resolved_callees": 1}, '
                '"filtered_pre_persist_buckets": {"zero_candidate_count": 2}}}}'
            ),
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["totals"]["call_site_funnel"] == {
        "observed_syntactic_callsites": 5,
        "filtered_pre_persist": 2,
        "persisted_callsites": 3,
        "persisted_accepted": 2,
        "persisted_dropped": 1,
        "record_drops": {"no_resolved_callees": 1},
        "conservation_ok": True,
    }
    assert payload["totals"]["filtered_pre_persist_buckets"] == {
        "zero_candidate_count": 2
    }
    python = {entry["language"]: entry for entry in payload["languages"]}["python"]
    assert python["call_site_funnel"]["persisted_callsites"] == 3
    assert python["call_site_funnel"]["record_drops"] == {"no_resolved_callees": 1}
    assert python["filtered_pre_persist_buckets"] == {"zero_candidate_count": 2}


def test_snapshot_report_counts_pairs_and_finalized_call_edges(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.upsert_callsite_pairs(
            conn,
            snapshot_id=snapshot_id,
            caller_id="meth_alpha",
            rows=[
                ("helper", "site-1", "func_alpha", "in_repo_candidate"),
                ("other", "site-2", "func_beta", "in_repo_candidate"),
            ],
        )
        artifact_write.upsert_node_calls(
            conn,
            caller_id="meth_alpha",
            callee_ids=("func_alpha", "func_beta"),
            call_hash="hash-meth-alpha",
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    python = {entry["language"]: entry for entry in payload["languages"]}["python"]
    assert python["callsite_pairs"] == {"count": 2}
    assert python["finalized_call_edges"] == {"count": 2}
    assert python["callsite_pairs_by_scope"]["non_tests"] == {"count": 2}
    assert python["finalized_call_edges_by_scope"]["non_tests"] == {"count": 2}
    assert payload["totals"]["callsite_pairs"] == {"count": 2}
    assert payload["totals"]["finalized_call_edges"] == {"count": 2}


def test_scope_bucket_detects_test_and_non_test_paths() -> None:
    assert exec_reporting._scope_bucket("pkg/service.py") == "non_tests"
    assert exec_reporting._scope_bucket("tests/test_api.py") == "tests"
    assert exec_reporting._scope_bucket("src/test/java/org/example/AppTest.java") == "tests"
