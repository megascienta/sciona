# SPDX-License-Identifier: MIT

from __future__ import annotations

import sqlite3

from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.pipelines.ops.build_artifacts import (
    _cleanup_temp_callsite_tables,
    _stored_call_resolution_diagnostics,
)


def test_stored_call_resolution_diagnostics_drops_bucket_and_observation_detail() -> None:
    payload = _stored_call_resolution_diagnostics(
        {
            "version": 1,
            "persisted_drop_observations": [{"identifier": "helper"}],
            "totals": {
                "observed_callsites": 3,
                "non_accepted_gate_reasons": {"insufficient_static_evidence": 2},
                "persisted_callsite_pair_expansion": {
                    "persisted_callsites": 1,
                },
            },
            "by_caller": {
                "meth_alpha": {
                    "observed_callsites": 3,
                    "non_accepted_gate_reasons": {
                        "insufficient_static_evidence": 2
                    },
                    "persisted_callsite_pair_expansion": {
                        "persisted_callsites": 1,
                    },
                }
            },
        }
    )

    assert "persisted_drop_observations" not in payload
    assert payload["totals"] == {"observed_callsites": 3}
    assert payload["by_caller"] == {
        "meth_alpha": {
            "observed_callsites": 3,
        }
    }


def test_cleanup_temp_callsite_tables_clears_observed_and_optional_rejected() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    artifact_write.store_temp_observed_callsites(
        conn,
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.run",
        caller_module="repo.pkg",
        caller_language="python",
        caller_file_path="pkg/run.py",
        rows=[
            (
                "helper",
                1,
                "terminal",
                None,
                None,
                None,
                None,
                None,
            )
        ],
    )
    artifact_write.store_temp_rejected_callsites(
        conn,
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.run",
        caller_module="repo.pkg",
        caller_language="python",
        caller_file_path="pkg/run.py",
        rows=[
            (
                (
                    "helper",
                    "dropped",
                    None,
                    None,
                    "no_candidates",
                    1,
                    "terminal",
                    None,
                    None,
                    1,
                    0,
                    None,
                ),
                "no_in_repo_candidate",
                "no_candidates",
                None,
            )
        ],
    )

    _cleanup_temp_callsite_tables(conn, retain_rejected_callsites=True)

    observed_count = conn.execute(
        "SELECT COUNT(*) FROM observed_callsites_temp"
    ).fetchone()[0]
    rejected_count = conn.execute(
        "SELECT COUNT(*) FROM rejected_callsites_temp"
    ).fetchone()[0]
    assert observed_count == 0
    assert rejected_count == 1

    _cleanup_temp_callsite_tables(conn, retain_rejected_callsites=False)

    rejected_count = conn.execute(
        "SELECT COUNT(*) FROM rejected_callsites_temp"
    ).fetchone()[0]
    assert rejected_count == 0
