# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.pipelines import repo as repo_pipeline
from sciona.runtime import constants as runtime_constants
from sciona.runtime import paths as runtime_paths


def test_snapshot_report_returns_db_counts(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot

    payload = repo_pipeline.snapshot_report(snapshot_id, repo_root=repo_root)
    assert payload is not None
    assert payload["snapshot_id"] == snapshot_id
    assert payload["totals"]["files"] == 3
    assert payload["totals"]["nodes"] == 5
    assert payload["totals"]["edges"] == 5
    assert payload["totals"]["call_sites"]["eligible"] == 0
    assert payload["totals"]["call_sites"]["accepted"] == 0
    assert payload["totals"]["call_sites"]["dropped"] == 0
    by_language = {entry["language"]: entry for entry in payload["languages"]}
    python = by_language["python"]
    assert python["call_sites"]["eligible"] == 0
    assert python["call_sites"]["accepted"] == 0
    assert python["call_sites"]["dropped"] == 0


def test_snapshot_report_full_includes_failure_reasons(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    artifact_db = repo_root / ".sciona" / runtime_constants.ARTIFACT_DB_FILENAME
    caller_qname = runtime_paths.repo_name_prefix(repo_root) + ".pkg.alpha.Service.run"

    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        conn.execute(
            """
            INSERT INTO call_sites(
                snapshot_id,
                caller_id,
                caller_qname,
                caller_node_type,
                identifier,
                resolution_status,
                accepted_callee_id,
                provenance,
                drop_reason,
                candidate_count,
                callee_kind,
                call_start_byte,
                call_end_byte,
                call_ordinal,
                site_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                "meth_alpha",
                caller_qname,
                "callable",
                "helper",
                "accepted",
                "func_alpha",
                "exact_qname",
                None,
                1,
                "terminal",
                None,
                None,
                1,
                "site-accepted",
            ),
        )
        conn.execute(
            """
            INSERT INTO call_sites(
                snapshot_id,
                caller_id,
                caller_qname,
                caller_node_type,
                identifier,
                resolution_status,
                accepted_callee_id,
                provenance,
                drop_reason,
                candidate_count,
                callee_kind,
                call_start_byte,
                call_end_byte,
                call_ordinal,
                site_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                "meth_alpha",
                caller_qname,
                "callable",
                "missing",
                "dropped",
                None,
                None,
                "unique_without_provenance",
                1,
                "terminal",
                None,
                None,
                2,
                "site-dropped",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    payload = repo_pipeline.snapshot_report(
        snapshot_id,
        repo_root=repo_root,
        include_failure_reasons=True,
    )
    assert payload is not None
    by_language = {entry["language"]: entry for entry in payload["languages"]}
    python = by_language["python"]
    call_sites = python["call_sites"]
    assert call_sites["eligible"] == 2
    assert call_sites["accepted"] == 1
    assert call_sites["dropped"] == 1
    assert python["drop_reasons"] == {"unique_without_provenance": 1}
    assert "unique_without_provenance" in python["drop_reason_examples"]
    example = python["drop_reason_examples"]["unique_without_provenance"][0]
    assert example["caller_qname"].endswith(".pkg.alpha.Service.run")
    assert example["caller_file_path"] == "pkg/alpha/service.py"
    assert example["identifier"] == "missing"
    assert example["candidate_count"] == 1
    assert example["callee_kind"] == "terminal"
    assert example["count"] == 1
    hotspots = payload["failure_hotspots"]
    top_callers = hotspots["top_failed_callers"]["python"]
    top_files = hotspots["top_failed_files"]["python"]
    assert top_callers[0]["name"].endswith(".pkg.alpha.Service.run")
    assert top_callers[0]["count"] == 1
    assert top_files[0]["name"] == "pkg/alpha/service.py"
    assert top_files[0]["count"] == 1
