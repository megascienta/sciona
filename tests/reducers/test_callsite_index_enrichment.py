# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
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
