# SPDX-License-Identifier: MIT

from __future__ import annotations

import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import rollups
from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.artifacts.call_resolution import resolve_callees
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
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
                SELECT identifier,
                       resolution_status,
                       candidate_count,
                       in_scope_candidate_count,
                       candidate_module_hints,
                       callee_kind,
                       call_ordinal
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
            assert rows[0]["in_scope_candidate_count"] == 1
            assert rows[0]["candidate_module_hints"]
            assert rows[0]["callee_kind"] == "terminal"
            assert rows[0]["call_ordinal"] == 1
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_resolve_callees_counts_each_identifier_once() -> None:
    resolved_ids, resolved_names, stats, rows = resolve_callees(
        ["helper"],
        {"helper": ["pkg.mod.helper"]},
        caller_module="pkg.mod",
        module_lookup={"pkg.mod.helper": "pkg.mod"},
        import_targets={"pkg.mod": set()},
        expanded_import_targets={"pkg.mod": set()},
        module_ancestors={"pkg.mod": set()},
    )

    assert resolved_ids == {"pkg.mod.helper"}
    assert resolved_names == {"helper"}
    assert stats["identifiers_total"] == 1
    assert stats["accepted_identifiers"] == 1
    assert stats["dropped_identifiers"] == 0
    assert rows[0][0] == "helper"


def test_call_sites_filter_out_of_repo_accepted_rows_at_persistence_boundary(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            {"func_alpha", "external_callable"},
            {"helper"},
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {"exact_qname": 1},
                "dropped_by_reason": {},
                "candidate_count_histogram": {1: 1},
            },
            [
                (
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
                    1,
                    f"{prefix}.pkg.alpha",
                ),
                (
                    "external.helper",
                    "accepted",
                    "external_callable",
                    "exact_qname",
                    None,
                    1,
                    "qualified",
                    None,
                    None,
                    2,
                    1,
                    "external",
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
                        callee_identifiers=("helper",),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            node_call_rows = artifact_conn.execute(
                """
                SELECT callee_id
                FROM node_calls
                WHERE caller_id = ?
                ORDER BY callee_id
                """,
                ("meth_alpha",),
            ).fetchall()
            assert [row["callee_id"] for row in node_call_rows] == ["func_alpha"]
            callsite_rows = artifact_conn.execute(
                """
                SELECT identifier, accepted_callee_id
                FROM call_sites
                WHERE snapshot_id = ? AND caller_id = ?
                ORDER BY call_ordinal
                """,
                (snapshot_id, "meth_alpha"),
            ).fetchall()
            assert [(row["identifier"], row["accepted_callee_id"]) for row in callsite_rows] == [
                ("helper", "func_alpha")
            ]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_call_sites_accept_export_chain_narrowed_provenance(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            {"func_alpha"},
            {"helper"},
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {"export_chain_narrowed": 1},
                "dropped_by_reason": {},
                "candidate_count_histogram": {1: 1},
            },
            [
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
                        callee_identifiers=("helper",),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            rows = artifact_conn.execute(
                """
                SELECT identifier, provenance
                FROM call_sites
                WHERE snapshot_id = ? AND caller_id = ?
                ORDER BY call_ordinal
                """,
                (snapshot_id, "meth_alpha"),
            ).fetchall()
            assert [(row["identifier"], row["provenance"]) for row in rows] == [
                ("helper", "export_chain_narrowed")
            ]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_node_calls_match_accepted_persisted_callsite_outcomes(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            {"func_alpha", "external_callable"},
            {"helper"},
            {
                "identifiers_total": 3,
                "accepted_by_provenance": {
                    "exact_qname": 1,
                    "export_chain_narrowed": 1,
                },
                "dropped_by_reason": {"ambiguous_no_in_scope_candidate": 1},
                "candidate_count_histogram": {1: 2, 3: 1},
            },
            [
                (
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
                    1,
                    f"{prefix}.pkg.alpha",
                ),
                (
                    "helper_alias",
                    "accepted",
                    "func_alpha",
                    "export_chain_narrowed",
                    None,
                    1,
                    "terminal",
                    None,
                    None,
                    2,
                    1,
                    f"{prefix}.pkg.alpha",
                ),
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
                    3,
                    0,
                    "vendor.external",
                ),
                (
                    "external.helper",
                    "accepted",
                    "external_callable",
                    "exact_qname",
                    None,
                    1,
                    "qualified",
                    None,
                    None,
                    4,
                    1,
                    "external",
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
                        callee_identifiers=("helper", "helper_alias", "vendor.external.unknownfn"),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            persisted_callsite_rows = artifact_conn.execute(
                """
                SELECT identifier, resolution_status, accepted_callee_id
                FROM call_sites
                WHERE snapshot_id = ? AND caller_id = ?
                ORDER BY call_ordinal
                """,
                (snapshot_id, "meth_alpha"),
            ).fetchall()
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

    assert [
        (
            row["identifier"],
            row["resolution_status"],
            row["accepted_callee_id"],
        )
        for row in persisted_callsite_rows
    ] == [
        ("helper", "accepted", "func_alpha"),
        ("helper_alias", "accepted", "func_alpha"),
        ("vendor.external.unknownfn", "dropped", None),
    ]
    assert [row["callee_id"] for row in node_call_rows] == ["func_alpha"]


def test_write_call_artifacts_clears_existing_node_calls_when_resolution_becomes_empty(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    record = CallExtractionRecord(
        caller_structural_id="meth_alpha",
        caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
        caller_node_type="callable",
        callee_identifiers=("helper",),
    )

    def _empty_resolve(*args, **kwargs):
        del args, kwargs
        return (
            set(),
            set(),
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {},
                "dropped_by_reason": {"no_candidates": 1},
                "candidate_count_histogram": {0: 1},
            },
            [],
        )

    try:
        artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
        try:
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=[record],
                eligible_callers={"meth_alpha"},
            )
            assert artifact_conn.execute(
                "SELECT COUNT(*) FROM node_calls WHERE caller_id = ?",
                ("meth_alpha",),
            ).fetchone()[0] == 1
            monkeypatch.setattr(rollups, "_resolve_callees", _empty_resolve)
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=[record],
                eligible_callers={"meth_alpha"},
            )
            assert artifact_conn.execute(
                "SELECT COUNT(*) FROM node_calls WHERE caller_id = ?",
                ("meth_alpha",),
            ).fetchone()[0] == 0
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_clears_existing_rows_when_no_call_records_remain(
    tmp_path: Path,
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    record = CallExtractionRecord(
        caller_structural_id="meth_alpha",
        caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
        caller_node_type="callable",
        callee_identifiers=("helper",),
    )
    try:
        artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
        try:
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=[record],
                eligible_callers={"meth_alpha"},
            )
            assert artifact_conn.execute(
                "SELECT COUNT(*) FROM node_calls WHERE caller_id = ?",
                ("meth_alpha",),
            ).fetchone()[0] == 1
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=[],
                eligible_callers={"meth_alpha"},
            )
            assert artifact_conn.execute(
                "SELECT COUNT(*) FROM node_calls WHERE caller_id = ?",
                ("meth_alpha",),
            ).fetchone()[0] == 0
            assert artifact_conn.execute(
                "SELECT COUNT(*) FROM call_sites WHERE snapshot_id = ? AND caller_id = ?",
                (snapshot_id, "meth_alpha"),
            ).fetchone()[0] == 0
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_reset_artifact_derived_state_clears_call_artifacts_and_rollups(
    tmp_path: Path,
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_conn.execute(
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
                in_scope_candidate_count,
                candidate_module_hints,
                site_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                "meth_alpha",
                "pkg.alpha.Service.run",
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
                1,
                "pkg.alpha",
                "site-hash",
            ),
        )
        artifact_conn.execute(
            """
            INSERT INTO node_calls(caller_id, callee_id, valid, call_hash)
            VALUES (?, ?, ?, ?)
            """,
            ("meth_alpha", "func_alpha", 1, "call-hash"),
        )
        artifact_conn.execute(
            """
            INSERT INTO module_call_edges(src_module_id, dst_module_id, call_count)
            VALUES (?, ?, ?)
            """,
            ("mod_alpha", "mod_beta", 1),
        )
        artifact_conn.commit()

        artifact_write.reset_artifact_derived_state(artifact_conn)

        assert artifact_conn.execute("SELECT COUNT(*) FROM call_sites").fetchone()[0] == 0
        assert artifact_conn.execute("SELECT COUNT(*) FROM node_calls").fetchone()[0] == 0
        assert artifact_conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0] == 0
        assert artifact_conn.execute("SELECT COUNT(*) FROM module_call_edges").fetchone()[0] == 0
    finally:
        artifact_conn.close()

def test_write_call_artifacts_rejects_duplicate_callers_before_writes(
    tmp_path: Path,
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        artifact_conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
        try:
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
                            callee_identifiers=("helper",),
                        ),
                        CallExtractionRecord(
                            caller_structural_id="meth_alpha",
                            caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
                            caller_node_type="callable",
                            callee_identifiers=("helper_alias",),
                        ),
                    ],
                    eligible_callers={"meth_alpha"},
                )
            except ValueError as exc:
                assert "Duplicate call artifact records" in str(exc)
            else:
                raise AssertionError("Expected duplicate caller records to raise")
            callsite_rows = artifact_conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM call_sites
                WHERE snapshot_id = ? AND caller_id = ?
                """,
                (snapshot_id, "meth_alpha"),
            ).fetchone()
            node_call_rows = artifact_conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM node_calls
                WHERE caller_id = ?
                """,
                ("meth_alpha",),
            ).fetchone()
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()

    assert callsite_rows["count"] == 0
    assert node_call_rows["count"] == 0


def test_call_sites_do_not_persist_zero_candidate_or_out_of_scope_observations(
    tmp_path: Path,
) -> None:
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
                        callee_identifiers=("print", "missing_symbol"),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            row = artifact_conn.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM call_sites
                WHERE snapshot_id = ? AND caller_id = ?
                """,
                (snapshot_id, "meth_alpha"),
            ).fetchone()
            assert row["row_count"] == 0
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()
