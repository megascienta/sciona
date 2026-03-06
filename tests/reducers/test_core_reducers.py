# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3
from pathlib import Path

import pytest

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.maintenance import rebuild_graph_index
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.data_storage.transactions import transaction
from sciona.reducers import (
    callable_overview,
    classifier_inheritance,
    classifier_overview,
    dependency_edges,
    file_outline,
    module_overview,
    snapshot_provenance,
    structural_index,
    symbol_lookup,
    symbol_references,
)
from sciona.reducers import callable_source, concatenated_source
from sciona.runtime import constants as setup_config
from sciona.runtime import paths as runtime_paths
from tests.helpers import core_conn as _core_conn, insert_snapshot, parse_json_payload, qualify_repo_name as _q, seed_repo_with_snapshot


def _build_profile_repo(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    def _pq(name: str) -> str:
        return f"{repo_prefix}.{name}"
    module_path = repo_root / "pkg" / "alpha"
    module_path.mkdir(parents=True)
    (module_path / "__init__.py").write_text("", encoding="utf-8")
    file_alpha = module_path / "service.py"
    file_alpha.write_text(
        '''"""Module doc."""\n\nfrom pkg.beta import worker as beta_worker\n\n@decorator("value")\nclass OrderService(BaseService, Mixin):\n    """Service doc."""\n    def method_one(self, user_id: str, *, force: bool = False):\n        """Method doc."""\n        return helper(user_id)\n\n\ndef helper(user_id, *args, **kwargs):\n    """Helper doc."""\n    return user_id\n\nbeta_worker.run()\n''',
        encoding="utf-8",
    )
    beta_path = repo_root / "pkg" / "beta"
    beta_path.mkdir(parents=True)
    (beta_path / "worker.py").write_text(
        "def run():\n    return True\n",
        encoding="utf-8",
    )
    ts_path = repo_root / "pkg" / "ts"
    ts_path.mkdir(parents=True)
    (ts_path / "service.ts").write_text(
        """import { helper } from "../alpha/service";

@sealed
export class WidgetService {
  public execute(userId: string, force?: boolean) {
    return helper(userId);
  }
}

export function createWidget(name: string): WidgetService {
  return new WidgetService();
}
""",
        encoding="utf-8",
    )

    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir(exist_ok=True)
    db_path = sciona_dir / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    snapshot_id = "snap_profile"
    insert_snapshot(conn, snapshot_id, structural_hash="profile-hash")

    ids = {
        "module_pkg_alpha": "mod_pkg_alpha",
        "module_alpha": "mod_alpha",
        "module_beta": "mod_beta",
        "class_order": "cls_order",
        "function_helper": "func_helper",
        "method_one": "meth_one",
        "module_ts": "mod_ts",
        "ts_class": "cls_ts",
        "ts_function": "func_ts",
    }
    nodes = [
        (
            ids["module_pkg_alpha"],
            "module",
            "python",
            _pq("pkg.alpha"),
            "pkg/alpha/__init__.py",
            1,
            1,
        ),
        (
            ids["module_alpha"],
            "module",
            "python",
            _pq("pkg.alpha.service"),
            "pkg/alpha/service.py",
            1,
            17,
        ),
        (
            ids["module_beta"],
            "module",
            "python",
            _pq("pkg.beta.worker"),
            "pkg/beta/worker.py",
            1,
            2,
        ),
        (
            ids["class_order"],
            "classifier",
            "python",
            _pq("pkg.alpha.service.OrderService"),
            "pkg/alpha/service.py",
            6,
            10,
        ),
        (
            ids["function_helper"],
            "callable",
            "python",
            _pq("pkg.alpha.service.helper"),
            "pkg/alpha/service.py",
            13,
            15,
        ),
        (
            ids["method_one"],
            "callable",
            "python",
            _pq("pkg.alpha.service.OrderService.method_one"),
            "pkg/alpha/service.py",
            8,
            10,
        ),
        (
            ids["module_ts"],
            "module",
            "typescript",
            _pq("pkg.ts.service"),
            "pkg/ts/service.ts",
            1,
            11,
        ),
        (
            ids["ts_class"],
            "classifier",
            "typescript",
            _pq("pkg.ts.service.WidgetService"),
            "pkg/ts/service.ts",
            3,
            8,
        ),
        (
            ids["ts_function"],
            "callable",
            "typescript",
            _pq("pkg.ts.service.createWidget"),
            "pkg/ts/service.ts",
            10,
            11,
        ),
    ]
    for (
        structural_id,
        node_type,
        language,
        qualified_name,
        file_path,
        start_line,
        end_line,
    ) in nodes:
        conn.execute(
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
        conn.execute(
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
                file_path,
                start_line,
                end_line,
                f"hash-{structural_id}",
            ),
        )

    edges = [
        (ids["module_alpha"], ids["class_order"], "LEXICALLY_CONTAINS"),
        (ids["module_alpha"], ids["function_helper"], "LEXICALLY_CONTAINS"),
        (ids["class_order"], ids["method_one"], "LEXICALLY_CONTAINS"),
        (ids["module_alpha"], ids["module_beta"], "IMPORTS_DECLARED"),
        (ids["module_ts"], ids["ts_class"], "LEXICALLY_CONTAINS"),
        (ids["module_ts"], ids["ts_function"], "LEXICALLY_CONTAINS"),
    ]
    for src, dst, edge_type in edges:
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, src, dst, edge_type),
        )

    conn.commit()
    artifact_conn = artifact_connect(sciona_dir / setup_config.ARTIFACT_DB_FILENAME)
    try:
        with transaction(artifact_conn):
            rebuild_graph_index(
                artifact_conn,
                core_conn=conn,
                snapshot_id=snapshot_id,
            )
    finally:
        artifact_conn.close()
    conn.close()
    return {
        "repo_root": repo_root,
        "db_path": db_path,
        "snapshot_id": snapshot_id,
        "ids": ids,
    }


def test_concatenated_source_codebase_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="codebase",
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    paths = {entry["path"] for entry in payload["files"]}
    assert "pkg/alpha/service.py" in paths
    assert "pkg/beta/__init__.py" in paths


def test_concatenated_source_excludes_meta_modules(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    (repo_root / "meta_dir").mkdir()
    conn = _core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT INTO synthetic_nodes(synthetic_id, node_type, created_snapshot_id)
            VALUES (?, ?, ?)
            """,
            ("mod_meta", "entry_point", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO synthetic_node_instances(
                instance_id, synthetic_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:mod_meta",
                "mod_meta",
                snapshot_id,
                "meta.module",
                "meta_dir",
                1,
                1,
                "hash-mod_meta",
            ),
        )
        conn.commit()
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="codebase",
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    paths = {entry["path"] for entry in payload["files"]}
    assert "meta_dir" not in paths


def test_concatenated_source_module_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="module",
            module_id=_q(repo_root, "pkg.alpha"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    paths = {entry["path"] for entry in payload["files"]}
    assert "pkg/alpha/service.py" in paths
    assert "pkg/beta/__init__.py" not in paths


def test_concatenated_source_classifier_scope(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = concatenated_source.render(
            snapshot_id,
            conn,
            repo_root,
            scope="classifier",
            classifier_id=_q(repo_root, "pkg.alpha.Service"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    paths = {entry["path"] for entry in payload["files"]}
    assert "pkg/alpha/service.py" in paths


def test_callable_source_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = callable_source.render(
            snapshot_id,
            conn,
            repo_root,
            callable_id=_q(repo_root, "pkg.alpha.service.helper"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["file_path"]
    assert payload["source"]


def test_callable_source_skips_directory_path(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    (repo_root / "pkg/dir_func").mkdir(parents=True, exist_ok=True)
    conn = _core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_dir", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_dir",
                "func_dir",
                snapshot_id,
                _q(repo_root, "pkg.alpha.dir_func"),
                "pkg/dir_func",
                1,
                1,
                "hash-func_dir",
            ),
        )
        conn.commit()
        payload_text = callable_source.render(
            snapshot_id,
            conn,
            repo_root,
            callable_id=_q(repo_root, "pkg.alpha.dir_func"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["file_path"] == "pkg/dir_func"
    assert payload["source"] is None


def test_symbol_lookup_reducer_returns_matches(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = symbol_lookup.render(
            snapshot_id,
            conn,
            repo_root,
            query=_q(repo_root, "pkg.alpha"),
            kind="module",
            limit=5,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["matches"]
    assert any(
        match["qualified_name"] == _q(repo_root, "pkg.alpha")
        for match in payload["matches"]
    )


def test_symbol_lookup_accepts_any_kind(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = symbol_lookup.render(
            snapshot_id,
            conn,
            repo_root,
            query=_q(repo_root, "pkg.alpha"),
            kind="any",
            limit=5,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["matches"]


def test_symbol_lookup_deterministic_prelimit_with_duplicate_names(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    duplicate_name = _q(repo_root, "pkg.duplicate.target")
    duplicate_paths = [
        "pkg/z_last.py",
        "pkg/y_last.py",
        "pkg/x_last.py",
        "pkg/w_last.py",
        "pkg/v_last.py",
        "pkg/a_first.py",
    ]
    try:
        for idx, file_path in enumerate(duplicate_paths):
            structural_id = f"dup_{idx}"
            conn.execute(
                """
                INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
                VALUES (?, ?, ?, ?)
                """,
                (structural_id, "callable", "python", snapshot_id),
            )
            conn.execute(
                """
                INSERT INTO node_instances(
                    instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{snapshot_id}:{structural_id}",
                    structural_id,
                    snapshot_id,
                    duplicate_name,
                    file_path,
                    1,
                    10,
                    f"hash-{structural_id}",
                ),
            )
        conn.commit()
        payload_text = symbol_lookup.render(
            snapshot_id,
            conn,
            repo_root,
            query=_q(repo_root, "pkg.duplicate.target"),
            kind="callable",
            limit=1,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["matches"]
    assert payload["matches"][0]["qualified_name"] == duplicate_name
    assert payload["matches"][0]["file_path"] == "pkg/a_first.py"


def test_symbol_references_returns_relationships(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = symbol_references.render(
            snapshot_id,
            conn,
            repo_root,
            query=_q(repo_root, "pkg.alpha"),
            kind="module",
            limit=5,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["matches"]
    assert payload["references"]


def test_symbol_references_can_filter_by_module(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_beta_helper", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_beta_helper",
                "func_beta_helper",
                snapshot_id,
                _q(repo_root, "pkg.beta.helper"),
                "pkg/beta/helper.py",
                1,
                10,
                "hash-func-beta-helper",
            ),
        )
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_beta", "func_beta_helper", "LEXICALLY_CONTAINS"),
        )
        conn.commit()
        payload_text = symbol_references.render(
            snapshot_id,
            conn,
            repo_root,
            query="helper",
            kind="callable",
            module_id=_q(repo_root, "pkg.alpha"),
            limit=10,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["resolved_module_id"] == _q(repo_root, "pkg.alpha")
    assert payload["resolved_module_structural_id"] == "mod_alpha"
    assert payload["matches"]
    assert all(
        str(match["qualified_name"]).startswith(_q(repo_root, "pkg.alpha"))
        for match in payload["matches"]
    )


def test_dependency_edges_reducer_returns_edges(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            module_id=_q(repo_root, "pkg.alpha"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["edge_count"] >= 1
    assert payload["committed_count"] == payload["edge_count"]
    assert payload["overlay_added_count"] == 0
    assert payload["overlay_removed_count"] == 0
    edge = payload["edges"][0]
    assert "from_module_structural_id" in edge
    assert "to_module_structural_id" in edge
    assert edge["edge_source"] == "sci"
    assert edge["row_origin"] == "committed"


def test_dependency_edges_filters_and_limit(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            from_module_id=_q(repo_root, "pkg.alpha"),
            edge_type="IMPORTS_DECLARED",
            limit=1,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["edge_count"] == 1
    assert payload["edges"][0]["edge_type"] == "IMPORTS_DECLARED"


def test_dependency_edges_query_filters_sources(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            query=_q(repo_root, "pkg.alpha"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["edges"]
    assert all(
        edge["from_module_qualified_name"].startswith(_q(repo_root, "pkg.alpha"))
        for edge in payload["edges"]
    )


def test_file_outline_returns_nodes(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = file_outline.render(
            snapshot_id,
            conn,
            repo_root,
            module_id=_q(repo_root, "pkg.alpha"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["files"]
    assert any(entry["nodes"] for entry in payload["files"])


def test_dependency_edges_direction_filters(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            module_id=_q(repo_root, "pkg.alpha"),
            direction="out",
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["edges"]
    assert all(
        edge["from_module_qualified_name"].startswith(_q(repo_root, "pkg.alpha"))
        for edge in payload["edges"]
    )
    conn = _core_conn(repo_root)
    try:
        payload_text = dependency_edges.render(
            snapshot_id,
            conn,
            repo_root,
            module_id=_q(repo_root, "pkg.alpha"),
            direction="in",
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["edges"]
    assert all(
        edge["to_module_qualified_name"].startswith(_q(repo_root, "pkg.alpha"))
        for edge in payload["edges"]
    )


def test_dependency_edges_rejects_invalid_direction(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="direction must be one of"):
            dependency_edges.render(
                snapshot_id,
                conn,
                repo_root,
                direction="sideways",
            )
    finally:
        conn.close()


def test_dependency_edges_rejects_non_positive_limit(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="limit must be positive"):
            dependency_edges.render(
                snapshot_id,
                conn,
                repo_root,
                limit=0,
            )
    finally:
        conn.close()


def test_dependency_edges_rejects_unsupported_edge_type(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="edge_type must be one of"):
            dependency_edges.render(
                snapshot_id,
                conn,
                repo_root,
                edge_type="CALLABLE_IMPORTS_DECLARED",
            )
    finally:
        conn.close()


def test_class_overview_requires_class_id(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    try:
        with pytest.raises(ValueError, match="requires 'classifier_id'"):
            classifier_overview.run(
                repo["snapshot_id"],
                conn=conn,
                classifier_id=None,
                repo_root=repo["repo_root"],
            )
    finally:
        conn.close()


def test_classifier_inheritance_requires_classifier_id(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    try:
        with pytest.raises(ValueError, match="Classifier identifier is required"):
            classifier_inheritance.render(
                repo["snapshot_id"],
                conn=conn,
                classifier_id=None,
                repo_root=repo["repo_root"],
            )
    finally:
        conn.close()


def test_structural_index_reducer_reports_modules_and_cycles(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    db_path = repo_root / setup_config.SCIONA_DIR_NAME / setup_config.DB_FILENAME
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    payload = structural_index.run(snapshot_id, conn=conn, repo_root=repo_root)
    conn.close()

    assert payload["projection"] == "structural_index"
    modules = payload["modules"]["entries"]
    assert modules[0]["module_qualified_name"] == _q(repo_root, "pkg.alpha")
    assert modules[0]["file_count"] == 2
    assert modules[0]["method_count"] == 2
    assert payload["files"]["count"] >= 2
    assert payload["classifiers"]["entries"][0]["qualified_name"].startswith(
        _q(repo_root, "pkg.alpha")
    )
    assert payload["functions"]["by_module"] == []
    assert payload["methods"]["by_module"][0]["module_qualified_name"] == _q(
        repo_root, "pkg.alpha"
    )
    edges = payload["imports"]["edges"]
    assert (
        edges[0]["from_module_qualified_name"]
        <= edges[0]["to_module_qualified_name"]
    )
    assert payload["import_cycles"][0]["module_qualified_names"] == [
        _q(repo_root, "pkg.alpha"),
        _q(repo_root, "pkg.beta"),
    ]
    file_entry = payload["files"]["entries"][0]
    assert set(file_entry.keys()) <= {"path", "module_qualified_name"}


def test_callable_overview_reducer_returns_python_metadata(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = callable_overview.run(
        repo["snapshot_id"],
        conn=conn,
        callable_id=repo["ids"]["function_helper"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_qualified_name"] == _q(repo["repo_root"], "pkg.alpha.service")
    assert payload["file_path"] == "pkg/alpha/service.py"
    assert payload["parameters"] == ["user_id", "*args", "**kwargs"]
    assert payload["signature"].startswith("helper(")
    assert payload["parent_structural_id"] == repo["ids"]["module_alpha"]
    assert "confidence" not in payload


def test_callable_overview_reducer_returns_typescript_metadata(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = callable_overview.run(
        repo["snapshot_id"],
        conn=conn,
        callable_id=repo["ids"]["ts_function"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["language"] == "typescript"
    assert payload["parameters"] == ["name"]
    assert payload["signature"].startswith("createWidget(name")
    assert payload["callable_role"] == "declared"
    assert payload["callable_role_source"] == "inferred_lexical_parent"
    assert "confidence" not in payload


def test_class_overview_reducer_exposes_methods_and_metadata(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = classifier_overview.run(
        repo["snapshot_id"],
        conn=conn,
        classifier_id=repo["ids"]["class_order"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_qualified_name"] == _q(repo["repo_root"], "pkg.alpha.service")
    assert payload["bases"] == ["BaseService", "Mixin"]
    assert payload["methods"] == [
        {
            "callable_id": repo["ids"]["method_one"],
            "qualified_name": _q(
                repo["repo_root"], "pkg.alpha.service.OrderService.method_one"
            ),
        }
    ]
    assert "confidence" not in payload


def test_class_inheritance_reducer_emits_base_edges(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload_text = classifier_inheritance.render(
        repo["snapshot_id"],
        conn=conn,
        classifier_id=repo["ids"]["class_order"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["classifier_id"] == repo["ids"]["class_order"]
    assert payload["incoming"] == []
    assert payload["incoming_count"] == 0
    assert payload["outgoing_count"] == 2
    assert payload["edge_source"] == "profile"
    assert payload["outgoing"] == [
        {
            "edge_type": "INHERITS",
            "related_structural_id": None,
            "related_qualified_name": "BaseService",
        },
        {
            "edge_type": "INHERITS",
            "related_structural_id": None,
            "related_qualified_name": "Mixin",
        },
    ]


def test_class_inheritance_reducer_handles_no_bases(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload_text = classifier_inheritance.render(
        repo["snapshot_id"],
        conn=conn,
        classifier_id=repo["ids"]["ts_class"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["classifier_id"] == repo["ids"]["ts_class"]
    assert payload["outgoing"] == []
    assert payload["outgoing_count"] == 0
    assert payload["incoming"] == []
    assert payload["incoming_count"] == 0
    assert payload["edge_source"] == "none"


def test_class_inheritance_prefers_core_edges_when_available(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        VALUES (?, ?, ?, ?)
        """,
        (
            repo["snapshot_id"],
            repo["ids"]["class_order"],
            repo["ids"]["ts_class"],
            "EXTENDS",
        ),
    )
    conn.commit()
    artifact_db_path = (
        repo["repo_root"] / setup_config.SCIONA_DIR_NAME / setup_config.ARTIFACT_DB_FILENAME
    )
    artifact_conn = artifact_connect(artifact_db_path)
    try:
        with transaction(artifact_conn):
            rebuild_graph_index(
                artifact_conn,
                core_conn=conn,
                snapshot_id=repo["snapshot_id"],
            )
    finally:
        artifact_conn.close()

    payload_text = classifier_inheritance.render(
        repo["snapshot_id"],
        conn=conn,
        classifier_id=repo["ids"]["class_order"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    payload = parse_json_payload(payload_text)
    assert payload["edge_source"] == "sci"
    assert payload["outgoing"] == [
        {
            "edge_type": "EXTENDS",
            "related_structural_id": repo["ids"]["ts_class"],
            "related_qualified_name": _q(repo["repo_root"], "pkg.ts.service.WidgetService"),
        }
    ]
    assert payload["incoming"] == []


def test_module_overview_reducer_lists_children_and_imports(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = module_overview.run(
        repo["snapshot_id"],
        conn=conn,
        module_id=_q(repo["repo_root"], "pkg.alpha.service"),
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_structural_id"] == repo["ids"]["module_alpha"]
    assert payload["module_qualified_name"] == _q(repo["repo_root"], "pkg.alpha.service")
    assert payload["files"] == ["pkg/alpha/service.py"]
    assert payload["file_count"] == 1
    assert payload["classifiers"][0]["qualified_name"] == _q(
        repo["repo_root"], "pkg.alpha.service.OrderService"
    )
    function_qnames = {entry["qualified_name"] for entry in payload["functions"]}
    assert _q(repo["repo_root"], "pkg.alpha.service.helper") in function_qnames
    assert _q(repo["repo_root"], "pkg.alpha.service.OrderService.method_one") in function_qnames
    assert payload["node_counts"] == {"classifiers": 1, "callables": 2}
    assert payload["language_breakdown"] == {"python": 3}
    assert payload["imports"] == [
        {
            "module_structural_id": repo["ids"]["module_beta"],
            "module_qualified_name": _q(repo["repo_root"], "pkg.beta.worker"),
        }
    ]
    assert payload["nested_classifiers"] == []
    assert "confidence" not in payload


def test_module_overview_reducer_expands_package_modules(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = module_overview.run(
        repo["snapshot_id"],
        conn=conn,
        module_id=_q(repo["repo_root"], "pkg.alpha"),
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_qualified_name"] == _q(repo["repo_root"], "pkg.alpha")
    assert payload["files"] == ["pkg/alpha/__init__.py", "pkg/alpha/service.py"]
    assert payload["file_count"] == 2
    assert payload["classifiers"][0]["qualified_name"] == _q(
        repo["repo_root"], "pkg.alpha.service.OrderService"
    )
    function_qnames = {entry["qualified_name"] for entry in payload["functions"]}
    assert _q(repo["repo_root"], "pkg.alpha.service.helper") in function_qnames
    assert _q(repo["repo_root"], "pkg.alpha.service.OrderService.method_one") in function_qnames
    assert payload["node_counts"] == {"classifiers": 1, "callables": 2}
    assert payload["imports"] == [
        {
            "module_structural_id": repo["ids"]["module_beta"],
            "module_qualified_name": _q(repo["repo_root"], "pkg.beta.worker"),
        }
    ]


def test_module_overview_include_file_map(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = module_overview.run(
        repo["snapshot_id"],
        conn=conn,
        module_id=_q(repo["repo_root"], "pkg.alpha"),
        repo_root=repo["repo_root"],
        include_file_map=True,
    )
    conn.close()

    assert payload["module_file_count"] >= 1
    assert payload["module_files"]
    assert any(
        entry["module_qualified_name"].startswith(_q(repo["repo_root"], "pkg.alpha"))
        for entry in payload["module_files"]
    )


def test_module_overview_reducer_exposes_nests_edges(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    repo_root = repo["repo_root"]
    snapshot_id = repo["snapshot_id"]
    outer_id = "cls_outer"
    inner_id = "cls_inner"
    outer_q = _q(repo_root, "pkg.alpha.service.Outer")
    inner_q = _q(repo_root, "pkg.alpha.service.Outer.Inner")
    module_alpha = repo["ids"]["module_alpha"]
    try:
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            (outer_id, "classifier", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            (inner_id, "classifier", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:{outer_id}",
                outer_id,
                snapshot_id,
                outer_q,
                "pkg/alpha/service.py",
                20,
                25,
                f"hash-{outer_id}",
            ),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:{inner_id}",
                inner_id,
                snapshot_id,
                inner_q,
                "pkg/alpha/service.py",
                21,
                24,
                f"hash-{inner_id}",
            ),
        )
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, module_alpha, outer_id, "LEXICALLY_CONTAINS"),
        )
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, outer_id, inner_id, "LEXICALLY_CONTAINS"),
        )
        conn.commit()
        artifact_conn = artifact_connect(
            repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
        )
        try:
            with transaction(artifact_conn):
                rebuild_graph_index(
                    artifact_conn,
                    core_conn=conn,
                    snapshot_id=snapshot_id,
                )
        finally:
            artifact_conn.close()
        payload = module_overview.run(
            snapshot_id,
            conn=conn,
            module_id=_q(repo_root, "pkg.alpha.service"),
            repo_root=repo_root,
        )
    finally:
        conn.close()

    class_qnames = {entry["qualified_name"] for entry in payload["classifiers"]}
    assert outer_q in class_qnames


def _insert_typescript_bound_callables(conn, repo: dict[str, object]) -> dict[str, str]:
    snapshot_id = repo["snapshot_id"]
    module_ts = repo["ids"]["module_ts"]
    repo_root = repo["repo_root"]
    outer_id = "func_ts_outer"
    default_id = "func_ts_default"
    tools_run_id = "func_ts_outer_tools_run"
    q_outer = _q(repo_root, "pkg.ts.service.outer")
    q_default = _q(repo_root, "pkg.ts.service.default")
    q_tools_run = _q(repo_root, "pkg.ts.service.outer.tools.run")
    for structural_id, qualified_name, start_line, end_line in (
        (outer_id, q_outer, 12, 16),
        (default_id, q_default, 17, 19),
        (tools_run_id, q_tools_run, 13, 14),
    ):
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            (structural_id, "callable", "typescript", snapshot_id),
        )
        conn.execute(
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
                "pkg/ts/service.ts",
                start_line,
                end_line,
                f"hash-{structural_id}",
            ),
        )
    conn.execute(
        """
        INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot_id, module_ts, outer_id, "LEXICALLY_CONTAINS"),
    )
    conn.execute(
        """
        INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot_id, module_ts, default_id, "LEXICALLY_CONTAINS"),
    )
    conn.execute(
        """
        INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        VALUES (?, ?, ?, ?)
        """,
        (snapshot_id, outer_id, tools_run_id, "LEXICALLY_CONTAINS"),
    )
    conn.commit()
    artifact_conn = artifact_connect(
        repo_root / setup_config.SCIONA_DIR_NAME / setup_config.ARTIFACT_DB_FILENAME
    )
    try:
        with transaction(artifact_conn):
            rebuild_graph_index(
                artifact_conn,
                core_conn=conn,
                snapshot_id=snapshot_id,
            )
    finally:
        artifact_conn.close()
    return {
        "outer_id": outer_id,
        "default_id": default_id,
        "tools_run_id": tools_run_id,
        "q_outer": q_outer,
        "q_default": q_default,
        "q_tools_run": q_tools_run,
    }


def test_callable_overview_reducer_exposes_bound_callable_roles(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    try:
        ids = _insert_typescript_bound_callables(conn, repo)
        default_payload = callable_overview.run(
            repo["snapshot_id"],
            conn=conn,
            callable_id=ids["default_id"],
            repo_root=repo["repo_root"],
        )
        tools_payload = callable_overview.run(
            repo["snapshot_id"],
            conn=conn,
            callable_id=ids["tools_run_id"],
            repo_root=repo["repo_root"],
        )
    finally:
        conn.close()

    assert default_payload["callable_role"] == "bound"
    assert default_payload["callable_role_source"] == "inferred_lexical_parent"
    assert tools_payload["callable_role"] == "bound"
    assert tools_payload["callable_role_source"] == "inferred_lexical_parent"


def test_file_outline_and_module_overview_include_default_and_object_bound_callables(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    try:
        ids = _insert_typescript_bound_callables(conn, repo)
        file_outline_payload = parse_json_payload(
            file_outline.render(
                repo["snapshot_id"],
                conn,
                repo["repo_root"],
                module_id=_q(repo["repo_root"], "pkg.ts.service"),
            )
        )
        module_payload = module_overview.run(
            repo["snapshot_id"],
            conn=conn,
            module_id=_q(repo["repo_root"], "pkg.ts.service"),
            repo_root=repo["repo_root"],
        )
    finally:
        conn.close()

    outlined_qnames = {
        node["qualified_name"]
        for file_entry in file_outline_payload["files"]
        for node in file_entry["nodes"]
        if node["node_type"] == "callable"
    }
    assert ids["q_default"] in outlined_qnames
    assert ids["q_tools_run"] in outlined_qnames

    module_callables = {entry["qualified_name"] for entry in module_payload["callables"]}
    assert ids["q_default"] in module_callables
    assert ids["q_tools_run"] in module_callables


def test_snapshot_provenance_returns_committed_snapshot_metadata(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = snapshot_provenance.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["snapshot_id"] == snapshot_id
    assert payload["structural_hash"] == "struct-state"
    assert payload["git_commit_sha"] == f"commit-{snapshot_id}"
    assert payload["artifact_available"] is True
    assert isinstance(payload["artifact_rebuild_consistent"], bool)


def test_snapshot_provenance_reports_missing_artifact_db(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_path = (
        repo_root
        / setup_config.SCIONA_DIR_NAME
        / setup_config.ARTIFACT_DB_FILENAME
    )
    artifact_path.unlink()
    conn = _core_conn(repo_root)
    try:
        payload_text = snapshot_provenance.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["snapshot_id"] == snapshot_id
    assert payload["artifact_available"] is False
    assert payload["artifact_rebuild_consistent"] is None
