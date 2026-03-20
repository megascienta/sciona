# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.code_analysis.artifacts.rollups import _resolve_callees
from sciona.code_analysis.languages.common.ir import LocalBindingFact
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.code_analysis.core.extract.calls import CallExtractionRecord
from sciona.runtime import paths as runtime_paths
from sciona.runtime.paths import get_artifact_db_path

from tests.helpers import seed_repo_with_snapshot


def test_write_call_artifacts_resolves_function(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
        try:
            statuses = {"meth_alpha": "added"}
            call_records = [
                CallExtractionRecord(
                    caller_structural_id="meth_alpha",
                    caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
                    caller_node_type="callable",
                    callee_identifiers=("helper",),
                )
            ]
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers=set(statuses),
            )
            rows = artifact_conn.execute(
                "SELECT callee_id, valid FROM node_calls WHERE caller_id = ? ORDER BY callee_id",
                ("meth_alpha",),
            ).fetchall()
            assert rows
            assert rows[0][0] == "func_alpha"
            assert rows[0][1] == 1
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_resolves_ambiguous_by_imports(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        additions = [
            ("mod_gamma", "module", "python", f"{prefix}.pkg.gamma", "pkg/gamma/__init__.py"),
            (
                "func_gamma",
                "callable",
                "python",
                f"{prefix}.pkg.gamma.helper",
                "pkg/gamma/helper.py",
            ),
            (
                "func_beta_task",
                "callable",
                "python",
                f"{prefix}.pkg.beta.task",
                "pkg/beta/task.py",
            ),
        ]
        for structural_id, node_type, language, qualified_name, path in additions:
            core_conn.execute(
                """
                INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    structural_id,
                    node_type,
                    language,
                    snapshot_id,
                ),
            )
            core_conn.execute(
                """
                INSERT INTO node_instances(
                    instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{snapshot_id}:{structural_id}",
                    structural_id,
                    snapshot_id,
                    qualified_name,
                    path,
                    1,
                    10,
                    f"hash-{structural_id}",
                ),
            )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_gamma", "func_gamma", "LEXICALLY_CONTAINS"),
        )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_beta", "func_beta_task", "LEXICALLY_CONTAINS"),
        )
        core_conn.commit()

        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
        try:
            call_records = [
                CallExtractionRecord(
                    caller_structural_id="func_beta_task",
                    caller_qualified_name=f"{prefix}.pkg.beta.task",
                    caller_node_type="callable",
                    callee_identifiers=("helper",),
                )
            ]
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers={"func_beta_task"},
            )
            rows = artifact_conn.execute(
                "SELECT callee_id FROM node_calls WHERE caller_id = ? ORDER BY callee_id",
                ("func_beta_task",),
            ).fetchall()
            assert rows
            assert rows[0][0] == "func_alpha"
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_resolves_fully_qualified_identifier(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
        try:
            call_records = [
                CallExtractionRecord(
                    caller_structural_id="meth_alpha",
                    caller_qualified_name=f"{prefix}.pkg.alpha.Service.run",
                    caller_node_type="callable",
                    callee_identifiers=(f"{prefix}.pkg.alpha.service.helper",),
                )
            ]
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers={"meth_alpha"},
            )
            rows = artifact_conn.execute(
                "SELECT callee_id FROM node_calls WHERE caller_id = ? ORDER BY callee_id",
                ("meth_alpha",),
            ).fetchall()
            assert rows
            assert rows[0][0] == "func_alpha"
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_accepts_export_chain_narrowed_resolution(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        additions = [
            (
                "func_alpha_alt",
                "callable",
                "python",
                f"{prefix}.pkg.alpha.alt.helper",
                "pkg/alpha/service.py",
            ),
            (
                "func_beta_task",
                "callable",
                "python",
                f"{prefix}.pkg.beta.task",
                "pkg/beta/task.py",
            ),
        ]
        for structural_id, node_type, language, qualified_name, path in additions:
            core_conn.execute(
                """
                INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    structural_id,
                    node_type,
                    language,
                    snapshot_id,
                ),
            )
            core_conn.execute(
                """
                INSERT INTO node_instances(
                    instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{snapshot_id}:{structural_id}",
                    structural_id,
                    snapshot_id,
                    qualified_name,
                    path,
                    1,
                    10,
                    f"hash-{structural_id}",
                ),
            )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_beta", "func_beta_task", "LEXICALLY_CONTAINS"),
        )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_alpha", "func_alpha_alt", "LEXICALLY_CONTAINS"),
        )
        core_conn.commit()

        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
        try:
            call_records = [
                CallExtractionRecord(
                    caller_structural_id="func_beta_task",
                    caller_qualified_name=f"{prefix}.pkg.beta.task",
                    caller_node_type="callable",
                    callee_identifiers=("helper",),
                )
            ]
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers={"func_beta_task"},
            )
            rows = artifact_conn.execute(
                "SELECT callee_id FROM node_calls WHERE caller_id = ? ORDER BY callee_id",
                ("func_beta_task",),
            ).fetchall()
            assert [row["callee_id"] for row in rows] == ["func_alpha_alt"]
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_write_call_artifacts_rejects_unique_without_provenance_and_reports_diagnostics(
    tmp_path: Path,
):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        core_conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_beta_task", "callable", "python", snapshot_id),
        )
        core_conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_beta_task",
                "func_beta_task",
                snapshot_id,
                f"{prefix}.pkg.beta.task",
                "pkg/beta/task.py",
                1,
                10,
                "hash-func_beta_task",
            ),
        )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_beta", "func_beta_task", "LEXICALLY_CONTAINS"),
        )
        core_conn.execute(
            """
            DELETE FROM edges
            WHERE snapshot_id = ?
              AND src_structural_id = ?
              AND dst_structural_id = ?
              AND edge_type = ?
            """,
            (snapshot_id, "mod_beta", "mod_alpha", "IMPORTS_DECLARED"),
        )
        core_conn.commit()

        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
        try:
            diagnostics: dict[str, object] = {}
            call_records = [
                CallExtractionRecord(
                    caller_structural_id="func_beta_task",
                    caller_qualified_name=f"{prefix}.pkg.beta.task",
                    caller_node_type="callable",
                    callee_identifiers=("helper",),
                )
            ]
            write_call_artifacts(
                artifact_conn=artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
                call_records=call_records,
                eligible_callers={"func_beta_task"},
                diagnostics=diagnostics,
            )
            rows = artifact_conn.execute(
                "SELECT callee_id FROM node_calls WHERE caller_id = ? ORDER BY callee_id",
                ("func_beta_task",),
            ).fetchall()
            assert rows == []

            by_caller = diagnostics.get("by_caller") or {}
            caller_diag = by_caller.get("func_beta_task") or {}
            dropped = caller_diag.get("dropped_by_reason") or {}
            assert dropped.get("unique_without_provenance") == 1
            histogram = caller_diag.get("candidate_count_histogram") or {}
            assert histogram.get("1") == 1
            record_drops = caller_diag.get("record_drops") or {}
            assert record_drops.get("no_resolved_callees") == 1
            assert caller_diag.get("observed_callsites") == 1
            assert caller_diag.get("persisted_callsites") == 0
            assert caller_diag.get("filtered_before_persist") == 1
            assert caller_diag.get("finalized_accepted_callsites") == 0
            assert caller_diag.get("finalized_dropped_callsites") == 0
            assert caller_diag.get("non_accepted_gate_reasons") == {
                "insufficient_static_evidence": 1
            }
            totals = diagnostics.get("totals") or {}
            assert totals.get("observed_callsites") == 1
            assert totals.get("persisted_callsites") == 0
            assert totals.get("filtered_before_persist") == 1
            assert totals.get("finalized_accepted_callsites") == 0
            assert totals.get("finalized_dropped_callsites") == 0
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()


def test_resolve_callees_accepts_parent_package_with_precomputed_ancestors() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("pkg.parent.reexported.fn",),
        {"fn": ["callee-id"]},
        caller_module="pkg.parent.child",
        module_lookup={"callee-id": "pkg.parent"},
        import_targets={"pkg.parent.child": {"pkg.parent.child", "pkg.parent"}},
        expanded_import_targets={"pkg.parent.child": {"pkg.parent.child", "pkg.parent"}},
        module_ancestors={"pkg.parent.child": {"pkg.parent"}},
    )
    assert resolved_ids == {"callee-id"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("import_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"


def test_resolve_callees_uses_binding_fact_direct_import_symbol_candidates() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("Matrix",),
        {},
        caller_module="sympy.client",
        caller_language="python",
        module_lookup={"id_matrix": "sympy.matrices.dense"},
        callable_qname_by_id={"id_matrix": "sympy.matrices.dense.Matrix"},
        import_targets={"sympy.client": {"sympy.matrices.dense"}},
        expanded_import_targets={"sympy.client": {"sympy.matrices.dense"}},
        module_ancestors={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="Matrix",
                target="sympy.matrices.dense.Matrix",
                binding_kind="direct_import_symbol",
                evidence_kind="syntax_local_import",
                language="python",
            ),
        ),
    )
    assert resolved_ids == {"id_matrix"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("import_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_matrix"


def test_resolve_callees_uses_binding_fact_module_alias_candidates() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("translator.translateKeys",),
        {},
        caller_module="nodebb.admin.dashboard",
        caller_language="javascript",
        module_lookup={"id_translate": "nodebb.public.src.translator"},
        callable_qname_by_id={
            "id_translate": "nodebb.public.src.translator.translateKeys"
        },
        import_targets={"nodebb.admin.dashboard": {"nodebb.public.src.translator"}},
        expanded_import_targets={"nodebb.admin.dashboard": {"nodebb.public.src.translator"}},
        module_ancestors={},
        local_binding_facts=(
            LocalBindingFact(
                symbol="translator",
                target="nodebb.public.src.translator",
                binding_kind="module_alias",
                evidence_kind="syntax_local_import",
                language="javascript",
            ),
        ),
    )
    assert resolved_ids == {"id_translate"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("exact_qname") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_translate"


def test_resolve_callees_rescues_python_unique_without_provenance_via_package_scope() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("pi",),
        {"pi": ["id_pi"]},
        caller_module="sympy.client",
        caller_language="python",
        module_lookup={"id_pi": "sympy.core.numbers"},
        callable_qname_by_id={"id_pi": "sympy.core.numbers.pi"},
        import_targets={
            "sympy.client": {"sympy.physics.mechanics"},
            "sympy.physics.mechanics": {"sympy.core.numbers"},
        },
        expanded_import_targets={"sympy.client": {"sympy.physics.mechanics"}},
        module_ancestors={},
        module_bindings_by_name={"sympy.core.numbers": {"pi"}},
        module_file_by_name={"sympy.physics.mechanics": "sympy/physics/mechanics/__init__.py"},
    )
    assert resolved_ids == {"id_pi"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("export_chain_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_pi"


def test_resolve_callees_rescues_python_no_candidates_via_package_surface_scope() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("sympy.pi",),
        {},
        caller_module="sympy.client",
        caller_language="python",
        module_lookup={"id_pi": "sympy.core.numbers"},
        callable_qname_by_id={"id_pi": "sympy.core.numbers.pi"},
        import_targets={
            "sympy.client": {"sympy"},
            "sympy": {"sympy.core"},
            "sympy.core": {"sympy.core.numbers"},
        },
        expanded_import_targets={"sympy.client": {"sympy"}},
        module_ancestors={},
        module_bindings_by_name={"sympy.core.numbers": {"pi"}},
        module_file_by_name={"sympy": "sympy/__init__.py"},
    )
    assert resolved_ids == {"id_pi"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("export_chain_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_pi"


def test_resolve_callees_rescues_typescript_unique_without_provenance_via_barrel_scope() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("create",),
        {"create": ["id_create"]},
        caller_module="app.feature.user",
        caller_language="typescript",
        module_lookup={"id_create": "app.core.factory"},
        callable_qname_by_id={"id_create": "app.core.factory.create"},
        import_targets={"app.feature.user": {"app.api"}},
        expanded_import_targets={"app.feature.user": {"app.api"}},
        module_ancestors={},
        module_bindings_by_name={
            "app.api": {"create"},
            "app.core.factory": {"create"},
        },
        module_file_by_name={"app.api": "src/api/index.ts"},
        ts_barrel_export_map={"app.feature.user": {"app.core.factory"}},
    )
    assert resolved_ids == {"id_create"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("export_chain_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_create"


def test_resolve_callees_rescues_javascript_unique_without_provenance_via_namespace_tail() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("colors.bold",),
        {"bold": ["id_bold"]},
        caller_module="app.ui",
        caller_language="javascript",
        module_lookup={"id_bold": "app.lib.colors"},
        callable_qname_by_id={"id_bold": "app.lib.colors.bold"},
        import_targets={"app.ui": {"app.colors"}},
        expanded_import_targets={"app.ui": {"app.colors"}},
        module_ancestors={},
        js_barrel_export_map={},
    )
    assert resolved_ids == {"id_bold"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("export_chain_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_bold"


def test_resolve_callees_rescues_javascript_no_candidates_via_index_barrel_scope() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("nodebb.src.user.index.getUsersFields",),
        {},
        caller_module="nodebb.src.topics.fork",
        caller_language="javascript",
        module_lookup={"id_getUsersFields": "nodebb.src.user.data"},
        callable_qname_by_id={
            "id_getUsersFields": "nodebb.src.user.data.getUsersFields"
        },
        import_targets={"nodebb.src.topics.fork": {"nodebb.src.user.index"}},
        expanded_import_targets={"nodebb.src.topics.fork": {"nodebb.src.user.index"}},
        module_ancestors={},
        js_barrel_export_map={"nodebb.src.topics.fork": {"nodebb.src.user.data"}},
    )
    assert resolved_ids == {"id_getUsersFields"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("export_chain_narrowed") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "id_getUsersFields"


def test_resolve_callees_accepts_single_index_proxy_qname_match() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("pkg.plugins.index.hooks.fire",),
        {"fire": ["plugins-hooks-fire"]},
        caller_module="pkg.consumer",
        caller_language="javascript",
        module_lookup={"plugins-hooks-fire": "pkg.plugins.hooks"},
        callable_qname_by_id={"plugins-hooks-fire": "pkg.plugins.hooks.fire"},
        import_targets={},
        expanded_import_targets={},
        module_ancestors={},
    )
    assert resolved_ids == {"plugins-hooks-fire"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("exact_qname") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "plugins-hooks-fire"


def test_resolve_callees_accepts_single_module_exports_proxy_qname_match() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("pkg.user.index.notifications.pushCount",),
        {"pushCount": ["user-notifications-pushcount"]},
        caller_module="pkg.api.chats",
        caller_language="javascript",
        module_lookup={"user-notifications-pushcount": "pkg.user.notifications"},
        callable_qname_by_id={
            "user-notifications-pushcount": (
                "pkg.user.notifications.module.exports.pushCount"
            )
        },
        import_targets={},
        expanded_import_targets={},
        module_ancestors={},
    )
    assert resolved_ids == {"user-notifications-pushcount"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("exact_qname") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "user-notifications-pushcount"


def test_resolve_callees_accepts_single_carrier_segment_qname_match() -> None:
    resolved_ids, _resolved_names, stats, callsite_rows = _resolve_callees(
        ("pkg.user.index.notifications.pushCount",),
        {"pushCount": ["user-notifications-pushcount"]},
        caller_module="pkg.api.chats",
        caller_language="javascript",
        module_lookup={"user-notifications-pushcount": "pkg.user.notifications"},
        callable_qname_by_id={
            "user-notifications-pushcount": (
                "pkg.user.notifications.UserNotifications.pushCount"
            )
        },
        import_targets={},
        expanded_import_targets={},
        module_ancestors={},
    )
    assert resolved_ids == {"user-notifications-pushcount"}
    accepted = stats.get("accepted_by_provenance") or {}
    assert accepted.get("exact_qname") == 1
    assert callsite_rows[0][1] == "accepted"
    assert callsite_rows[0][2] == "user-notifications-pushcount"


def test_write_call_artifacts_records_zero_candidate_non_accepted_gate_reason(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    diagnostics: dict[str, object] = {}
    try:
        artifact_conn = artifact_connect(
            get_artifact_db_path(repo_root), repo_root=repo_root
        )
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
                        callee_identifiers=("print",),
                    )
                ],
                eligible_callers={"meth_alpha"},
                diagnostics=diagnostics,
            )
            by_caller = diagnostics.get("by_caller") or {}
            caller_diag = by_caller.get("meth_alpha") or {}
            assert caller_diag.get("observed_callsites") == 1
            assert caller_diag.get("persisted_callsites") == 0
            assert caller_diag.get("filtered_before_persist") == 1
            assert caller_diag.get("non_accepted_gate_reasons") == {
                "no_in_repo_candidate": 1
            }
            totals = diagnostics.get("totals") or {}
            assert totals.get("non_accepted_gate_reasons") == {
                "no_in_repo_candidate": 1
            }
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()
