# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db import write_index as artifact_write
from sciona.reducers import callsite_index
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import core_conn as _core_conn, parse_json_payload, seed_repo_with_snapshot


def test_callsite_index_enrichment_is_opt_in(tmp_path: Path) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    conn = _core_conn(repo_root)
    artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        write_call_artifacts(
            artifact_conn=artifact_conn,
            core_conn=conn,
            snapshot_id=snapshot_id,
            call_records=[
                CallExtractionRecord(
                    caller_structural_id="meth_alpha",
                    caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
                    caller_node_type="callable",
                    callee_identifiers=("helper",),
                )
            ],
            eligible_callers={"meth_alpha"},
        )
        artifact_conn.commit()
        without_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
            )
        )
        assert without_payload["call_sites"] == []
        assert without_payload["resolution_diagnostics"] == {}

        with_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
                include_callsite_diagnostics=True,
            )
        )
        assert with_payload["call_sites"]
    finally:
        artifact_conn.close()
        conn.close()


def test_callsite_index_filters_callsites_and_edges(tmp_path: Path) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    conn = _core_conn(repo_root)
    artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.upsert_call_sites(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id="meth_alpha",
            caller_qname=f"{prefix}.pkg.alpha.Service.run",
            caller_node_type="callable",
            rows=[
                (
                    "helper",
                    "accepted",
                    "func_alpha",
                    "export_chain_narrowed",
                    None,
                    1,
                    "terminal",
                    None,
                    None,
                    1,
                    1,
                    f"{prefix}.pkg.alpha",
                ),
                (
                    "missing_helper",
                    "dropped",
                    None,
                    None,
                    "unique_without_provenance",
                    1,
                    "terminal",
                    None,
                    None,
                    2,
                    0,
                    f"{prefix}.pkg.beta",
                ),
            ],
        )
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO graph_edges(src_node_id, dst_node_id, edge_kind)
            VALUES (?, ?, ?)
            """,
            ("meth_alpha", "func_alpha", "CALLS"),
        )
        artifact_conn.commit()

        accepted_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
                status="accepted",
                provenance="export_chain_narrowed",
            )
        )
        assert [row["identifier"] for row in accepted_payload["call_sites"]] == ["helper"]
        assert [edge["callee_id"] for edge in accepted_payload["edges"]] == ["func_alpha"]

        dropped_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
                status="dropped",
                drop_reason="unique_without_provenance",
            )
        )
        assert [row["identifier"] for row in dropped_payload["call_sites"]] == [
            "missing_helper"
        ]
        assert dropped_payload["edges"] == []

        identifier_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
                identifier="helper",
            )
        )
        assert [row["identifier"] for row in identifier_payload["call_sites"]] == ["helper"]
    finally:
        artifact_conn.close()
        conn.close()
