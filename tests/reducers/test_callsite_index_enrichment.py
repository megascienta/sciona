# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
import json

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.reducers import callsite_index
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import core_conn as _core_conn, parse_json_payload, seed_repo_with_snapshot


def _set_call_resolution_diagnostics(
    conn,
    *,
    snapshot_id: str,
    caller_id: str,
    accepted_by_provenance: dict[str, int] | None = None,
    dropped_by_reason: dict[str, int] | None = None,
    observed_callsites: int = 0,
    persisted_callsites: int = 0,
    finalized_accepted_callsites: int = 0,
    finalized_dropped_callsites: int = 0,
) -> None:
    artifact_write.set_rebuild_metadata(
        conn,
        key=f"call_resolution_diagnostics:{snapshot_id}",
        value=json.dumps(
            {
                "version": 1,
                "by_caller": {
                    caller_id: {
                        "identifiers_total": observed_callsites,
                        "accepted_identifiers": finalized_accepted_callsites,
                        "dropped_identifiers": finalized_dropped_callsites,
                        "accepted_by_provenance": accepted_by_provenance or {},
                        "dropped_by_reason": dropped_by_reason or {},
                        "candidate_count_histogram": {},
                        "record_drops": {},
                        "filtered_pre_persist_buckets": {},
                        "observed_callsites": observed_callsites,
                        "persisted_callsites": persisted_callsites,
                        "filtered_before_persist": max(
                            0, observed_callsites - persisted_callsites
                        ),
                        "finalized_accepted_callsites": finalized_accepted_callsites,
                        "finalized_dropped_callsites": finalized_dropped_callsites,
                        "rescue_accepted_callsites": 0,
                    }
                },
            },
            sort_keys=True,
        ),
    )


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
        assert without_payload["callsite_pairs"] == []
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
        assert (
            with_payload["callsite_pairs_semantics"]
            == "deduplicated_persisted_in_scope_candidate_pairs"
        )
        assert with_payload["callsite_pairs"]
    finally:
        artifact_conn.close()
        conn.close()


def test_callsite_index_filters_callsites_and_edges(tmp_path: Path) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    conn = _core_conn(repo_root)
    artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.upsert_callsite_pairs(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id="meth_alpha",
            rows=[
                (
                    "helper",
                    "site-helper",
                    "func_alpha",
                    "in_repo_candidate",
                ),
                (
                    "missing_helper",
                    "site-missing",
                    "func_gamma",
                    "in_repo_candidate",
                ),
            ],
        )
        _set_call_resolution_diagnostics(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id="meth_alpha",
            accepted_by_provenance={"export_chain_narrowed": 1},
            dropped_by_reason={"unique_without_provenance": 1},
            observed_callsites=2,
            persisted_callsites=2,
            finalized_accepted_callsites=1,
            finalized_dropped_callsites=1,
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
                identifier="helper",
            )
        )
        assert [row["identifier"] for row in accepted_payload["callsite_pairs"]] == ["helper"]
        assert accepted_payload["callsite_pairs"][0]["row_origin"] == "committed"
        assert accepted_payload["callsite_pairs"][0]["transition"] == "unchanged"
        assert [edge["callee_id"] for edge in accepted_payload["edges"]] == ["func_alpha"]
        assert accepted_payload["edges"][0]["row_origin"] == "committed"
        assert accepted_payload["edges"][0]["transition"] == "unchanged"
        assert accepted_payload["edge_transition_summary"]["unchanged"] == 1

        identifier_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
                identifier="helper",
            )
        )
        assert [row["identifier"] for row in identifier_payload["callsite_pairs"]] == ["helper"]

        compact_payload = parse_json_payload(
            callsite_index.render(
                snapshot_id,
                conn=conn,
                repo_root=repo_root,
                callable_id="meth_alpha",
                compact=True,
            )
        )
        assert compact_payload["payload_kind"] == "compact_summary"
        assert compact_payload["pair_kind_counts"][0]["name"] == "in_repo_candidate"
        assert compact_payload["identifier_preview"]["entries"][0]["name"] == "helper"
        assert compact_payload["edge_preview"]["count"] == 1
    finally:
        artifact_conn.close()
        conn.close()
