# SPDX-License-Identifier: MIT

from __future__ import annotations

import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import rollups
from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.artifacts.call_resolution import (
    callsite_pair_rows,
    resolve_callees,
)
from sciona.code_analysis.languages.common.ir import LocalBindingFact
from sciona.code_analysis.core.extract.calls import (
    CallExtractionRecord,
    RejectedObservation,
)
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import seed_repo_with_snapshot


def test_write_call_artifacts_persists_in_repo_node_calls_only(tmp_path: Path) -> None:
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
                SELECT callee_id
                FROM node_calls
                WHERE caller_id = ?
                ORDER BY callee_id
                """,
                ("meth_alpha",),
            ).fetchall()
            assert [tuple(row) for row in rows] == [("func_alpha",)]
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


def test_callsite_pair_rows_expand_ambiguous_in_scope_candidates() -> None:
    rows = [
        (
            "helper",
            "dropped",
            None,
            None,
            "ambiguous_multiple_in_scope_candidates",
            2,
            "terminal",
            None,
            None,
            1,
            2,
            "pkg.alpha,pkg.beta",
        )
    ]

    pair_rows = callsite_pair_rows(
        rows,
        in_repo_callable_ids={"alpha_helper", "beta_helper"},
        symbol_index={"helper": ["alpha_helper", "beta_helper"]},
        caller_module="pkg.app",
        caller_language="python",
        module_lookup={
            "alpha_helper": "pkg.alpha",
            "beta_helper": "pkg.beta",
        },
        callable_qname_by_id={
            "alpha_helper": "pkg.alpha.helper",
            "beta_helper": "pkg.beta.helper",
        },
        import_targets={"pkg.app": {"pkg.alpha", "pkg.beta"}},
        expanded_import_targets={"pkg.app": {"pkg.alpha", "pkg.beta"}},
        module_ancestors={"pkg.app": {"pkg"}},
    )

    assert pair_rows == [
        ("helper", 1, "alpha_helper", "in_repo_candidate"),
        ("helper", 1, "beta_helper", "in_repo_candidate"),
    ]


def test_write_call_artifacts_dedupes_repeated_same_target_calls(tmp_path: Path) -> None:
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
                        callee_identifiers=("helper", "helper"),
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
            assert [tuple(row) for row in node_call_rows] == [("func_alpha",)]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_callsite_pairs_filter_out_of_repo_accepted_rows_at_persistence_boundary(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    diagnostics: dict[str, object] = {}

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
                diagnostics=diagnostics,
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
            totals = diagnostics.get("totals") or {}
            assert totals.get("non_accepted_gate_reasons") == {
                "outside_in_repo_scope": 1
            }
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_callsite_pairs_record_invalid_observation_shape_bucket_for_invalid_rows(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    diagnostics: dict[str, object] = {}

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            set(),
            set(),
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {},
                "dropped_by_reason": {},
                "candidate_count_histogram": {1: 1},
            },
            [
                (
                    "helper",
                    "accepted",
                    "func_alpha",
                    "unsupported_provenance_value",
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
                diagnostics=diagnostics,
            )
            rows = artifact_conn.execute(
                """
                SELECT COUNT(*) AS row_count
                FROM node_calls
                WHERE caller_id = ?
                """,
                ("meth_alpha",),
            ).fetchone()
            assert rows["row_count"] == 0
            totals = diagnostics.get("totals") or {}
            assert totals.get("non_accepted_gate_reasons") == {
                "invalid_observation_shape": 1
            }
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_accepts_export_chain_narrowed_provenance(
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
                SELECT callee_id
                FROM node_calls
                WHERE caller_id = ?
                ORDER BY callee_id
                """,
                ("meth_alpha",),
            ).fetchall()
            assert [tuple(row) for row in rows] == [("func_alpha",)]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_records_pair_expansion_diagnostics(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    diagnostics: dict[str, object] = {}

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            {"func_alpha"},
            {"helper", "other"},
            {
                "identifiers_total": 2,
                "accepted_by_provenance": {"exact_qname": 1},
                "dropped_by_reason": {"unique_without_provenance": 1},
                "candidate_count_histogram": {1: 2},
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
                    "other",
                    "dropped",
                    None,
                    None,
                    "unique_without_provenance",
                    1,
                    "terminal",
                    None,
                    None,
                    1,
                    0,
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
                        callee_identifiers=("helper", "other"),
                    )
                ],
                eligible_callers={"meth_alpha"},
                diagnostics=diagnostics,
            )
            expansion = (diagnostics.get("totals") or {}).get(
                "persisted_callsite_pair_expansion"
            ) or {}
            assert expansion == {
                "persisted_callsites": 1,
                "persisted_callsites_with_zero_pairs": 0,
                "persisted_callsites_with_one_pair": 1,
                "persisted_callsites_with_multiple_pairs": 0,
                "max_pairs_for_single_persisted_callsite": 1,
            }
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_stores_all_rejected_rows_in_temp_table(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    diagnostics: dict[str, object] = {}

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            set(),
            {"helper"},
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {},
                "dropped_by_reason": {"ambiguous_multiple_in_scope_candidates": 1},
                "candidate_count_histogram": {2: 1},
            },
            [
                (
                    "socket.in(room).emit",
                    "dropped",
                    None,
                    None,
                    "ambiguous_multiple_in_scope_candidates",
                    2,
                    "qualified",
                    None,
                    None,
                    1,
                    2,
                    f"{prefix}.pkg.alpha,{prefix}.pkg.beta",
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
                        callee_identifiers=("socket.in(room).emit",),
                    )
                ],
                eligible_callers={"meth_alpha"},
                diagnostics=diagnostics,
            )
            rows = artifact_conn.execute(
                """
                SELECT identifier, gate_reason, raw_drop_reason
                FROM rejected_callsites_temp
                ORDER BY call_ordinal
                """
            ).fetchall()
            assert [
                (row["identifier"], row["gate_reason"], row["raw_drop_reason"])
                for row in rows
            ] == [
                (
                    "socket.in(room).emit",
                    "insufficient_static_evidence",
                    "ambiguous_multiple_in_scope_candidates",
                ),
                ("external.helper", "outside_in_repo_scope", None),
            ]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_stores_local_binding_fields_in_temp_table(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            set(),
            {"translator.translateKeys"},
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {},
                "dropped_by_reason": {"no_candidates": 1},
                "candidate_count_histogram": {1: 1},
            },
            [
                (
                    "translator.translateKeys",
                    "dropped",
                    None,
                    None,
                    "no_candidates",
                    1,
                    "qualified",
                    None,
                    None,
                    1,
                    0,
                    None,
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
                        callee_identifiers=("translator.translateKeys",),
                        local_binding_facts=(
                            LocalBindingFact(
                                symbol="translator",
                                target=f"{prefix}.public.src.translator",
                                binding_kind="module_alias",
                                evidence_kind="syntax_local_import",
                                language="javascript",
                            ),
                        ),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            row = artifact_conn.execute(
                """
                SELECT local_binding_symbol, local_binding_target, local_binding_kind
                FROM rejected_callsites_temp
                WHERE identifier = 'translator.translateKeys'
                """
            ).fetchone()
            assert row is not None
            assert tuple(row) == (
                "translator",
                f"{prefix}.public.src.translator",
                "module_alias",
            )
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_stores_no_candidate_misses_in_rejected_temp_table(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, rejected_observations, **kwargs):
        del args, kwargs
        rejected_observations.append(
            RejectedObservation(
                identifier=f"{prefix}.pkg.models.Secret",
                ordinal=1,
                callee_kind="qualified",
                candidate_module_hints=(f"{prefix}.pkg.models",),
            )
        )
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
                        callee_identifiers=(f"{prefix}.pkg.models.Secret",),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            row = artifact_conn.execute(
                """
                SELECT identifier, gate_reason, candidate_count, candidate_module_hints
                FROM rejected_callsites_temp
                WHERE caller_structural_id = 'meth_alpha'
                """
            ).fetchone()
            assert row is not None
            assert tuple(row) == (
                f"{prefix}.pkg.models.Secret",
                "no_in_repo_candidate",
                0,
                f"{prefix}.pkg.models",
            )
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_stores_observed_callsites_temp_rows(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return set(), set(), {"identifiers_total": 2}, []

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
                        callee_identifiers=("translator.translateKeys", "helper"),
                        local_binding_facts=(
                            LocalBindingFact(
                                symbol="translator",
                                target=f"{prefix}.public.src.translator",
                                binding_kind="module_alias",
                                evidence_kind="syntax_local_import",
                                language="javascript",
                            ),
                        ),
                    )
                ],
                eligible_callers={"meth_alpha"},
            )
            rows = artifact_conn.execute(
                """
                SELECT
                    identifier,
                    call_ordinal,
                    callee_kind,
                    local_binding_symbol,
                    local_binding_kind
                FROM observed_callsites_temp
                ORDER BY call_ordinal
                """
            ).fetchall()
            assert [tuple(row) for row in rows] == [
                ("translator.translateKeys", 1, "qualified", "translator", "module_alias"),
                ("helper", 2, "terminal", None, None),
            ]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_records_multi_pair_expansion_diagnostics(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    diagnostics: dict[str, object] = {}

    def _fake_resolve_callees(*args, **kwargs):
        del args, kwargs
        return (
            set(),
            {"helper"},
            {
                "identifiers_total": 1,
                "accepted_by_provenance": {},
                "dropped_by_reason": {"ambiguous_multiple_in_scope_candidates": 1},
                "candidate_count_histogram": {2: 1},
            },
            [
                (
                    "helper",
                    "dropped",
                    None,
                    None,
                    "ambiguous_multiple_in_scope_candidates",
                    2,
                    "terminal",
                    None,
                    None,
                    1,
                    2,
                    f"{prefix}.pkg.alpha,{prefix}.pkg.beta",
                ),
            ],
        )

    def _fake_callsite_pair_rows(*args, **kwargs):
        del args, kwargs
        return [
            ("helper", 1, "func_alpha", "in_repo_candidate"),
            ("helper", 1, "func_beta", "in_repo_candidate"),
        ]

    monkeypatch.setattr(rollups, "_resolve_callees", _fake_resolve_callees)
    monkeypatch.setattr(rollups, "_callsite_pair_rows", _fake_callsite_pair_rows)
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
                diagnostics=diagnostics,
            )
            expansion = (diagnostics.get("totals") or {}).get(
                "persisted_callsite_pair_expansion"
            ) or {}
            assert expansion == {
                "persisted_callsites": 0,
                "persisted_callsites_with_zero_pairs": 0,
                "persisted_callsites_with_one_pair": 0,
                "persisted_callsites_with_multiple_pairs": 0,
                "max_pairs_for_single_persisted_callsite": 0,
            }
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

def test_node_calls_remain_empty_when_strict_accepts_none(
    tmp_path: Path, monkeypatch
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
                "dropped_by_reason": {"ambiguous_multiple_in_scope_candidates": 1},
                "candidate_count_histogram": {2: 1},
            },
            [
                (
                    "helper",
                    "dropped",
                    None,
                    None,
                    "ambiguous_multiple_in_scope_candidates",
                    2,
                    "terminal",
                    None,
                    None,
                    1,
                    2,
                    f"{prefix}.pkg.alpha,{prefix}.pkg.beta",
                ),
            ],
        )

    def _fake_callsite_pair_rows(*args, **kwargs):
        del args, kwargs
        return [
            ("helper", 1, "func_alpha", "in_repo_candidate"),
            ("helper", 1, "func_beta_helper", "in_repo_candidate"),
        ]

    core_conn.execute(
        """
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
        VALUES (?, ?, ?, ?)
        """,
        ("func_beta_helper", "callable", "python", snapshot_id),
    )
    core_conn.execute(
        """
        INSERT INTO node_instances(
            instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"{snapshot_id}:func_beta_helper",
            "func_beta_helper",
            snapshot_id,
            f"{prefix}.pkg.beta.helper",
            "pkg/beta/helper.py",
            1,
            5,
            "hash-func-beta-helper",
        ),
    )
    core_conn.execute(
        """
        INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot_id, "mod_beta", "func_beta_helper", "LEXICALLY_CONTAINS"),
    )
    core_conn.commit()

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
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()

    assert [row["callee_id"] for row in node_call_rows] == []


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

    assert node_call_rows["count"] == 0


def test_callsite_pairs_do_not_persist_zero_candidate_or_out_of_scope_observations(
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
                FROM node_calls
                WHERE caller_id = ?
                """,
                ("meth_alpha",),
            ).fetchone()
            assert row["row_count"] == 0
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()
