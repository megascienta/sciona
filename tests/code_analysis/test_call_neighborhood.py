# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3
from pathlib import Path

from sciona.code_analysis.artifacts import write_call_artifacts
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.code_analysis.tools.call_extraction import CallExtractionRecord
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
                    caller_node_type="method",
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
                "function",
                "python",
                f"{prefix}.pkg.gamma.helper",
                "pkg/gamma/helper.py",
            ),
            (
                "func_beta_task",
                "function",
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
            (snapshot_id, "mod_gamma", "func_gamma", "CONTAINS"),
        )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_beta", "func_beta_task", "CONTAINS"),
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
                    caller_node_type="function",
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
                    caller_node_type="method",
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


def test_write_call_artifacts_skips_ambiguous_same_module_resolution(tmp_path: Path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    prefix = runtime_paths.repo_name_prefix(repo_root)
    core_conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    try:
        additions = [
            (
                "func_alpha_alt",
                "function",
                "python",
                f"{prefix}.pkg.alpha.alt.helper",
                "pkg/alpha/service.py",
            ),
            (
                "func_beta_task",
                "function",
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
            (snapshot_id, "mod_beta", "func_beta_task", "CONTAINS"),
        )
        core_conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_alpha", "func_alpha_alt", "CONTAINS"),
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
                    caller_node_type="function",
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
            assert rows == []
        finally:
            artifact_conn.close()
    finally:
        core_conn.close()
