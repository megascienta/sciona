# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3
from pathlib import Path

from sciona.runtime import constants as setup_config
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.maintenance import rebuild_graph_index
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.data_storage.transactions import transaction
from sciona.reducers.core import (
    callable_overview,
    class_overview,
    module_overview,
)
from tests.helpers import insert_snapshot


def _build_profile_repo(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
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
            "pkg.alpha",
            "pkg/alpha/__init__.py",
            1,
            1,
        ),
        (
            ids["module_alpha"],
            "module",
            "python",
            "pkg.alpha.service",
            "pkg/alpha/service.py",
            1,
            17,
        ),
        (
            ids["module_beta"],
            "module",
            "python",
            "pkg.beta.worker",
            "pkg/beta/worker.py",
            1,
            2,
        ),
        (
            ids["class_order"],
            "class",
            "python",
            "pkg.alpha.service.OrderService",
            "pkg/alpha/service.py",
            6,
            10,
        ),
        (
            ids["function_helper"],
            "function",
            "python",
            "pkg.alpha.service.helper",
            "pkg/alpha/service.py",
            13,
            15,
        ),
        (
            ids["method_one"],
            "method",
            "python",
            "pkg.alpha.service.OrderService.method_one",
            "pkg/alpha/service.py",
            8,
            10,
        ),
        (
            ids["module_ts"],
            "module",
            "typescript",
            "pkg.ts.service",
            "pkg/ts/service.ts",
            1,
            11,
        ),
        (
            ids["ts_class"],
            "class",
            "typescript",
            "pkg.ts.service.WidgetService",
            "pkg/ts/service.ts",
            3,
            8,
        ),
        (
            ids["ts_function"],
            "function",
            "typescript",
            "pkg.ts.service.createWidget",
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
        (ids["module_alpha"], ids["class_order"], "CONTAINS"),
        (ids["module_alpha"], ids["function_helper"], "CONTAINS"),
        (ids["class_order"], ids["method_one"], "DEFINES_METHOD"),
        (ids["module_alpha"], ids["module_beta"], "IMPORTS_DECLARED"),
        (ids["module_ts"], ids["ts_class"], "CONTAINS"),
        (ids["module_ts"], ids["ts_function"], "CONTAINS"),
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


def test_callable_overview_reducer_returns_python_metadata(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = callable_overview.run(
        repo["snapshot_id"],
        conn=conn,
        function_id=repo["ids"]["function_helper"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_qualified_name"] == "pkg.alpha.service"
    assert payload["file_path"] == "pkg/alpha/service.py"
    assert payload["parameters"] == ["user_id", "*args", "**kwargs"]
    assert payload["signature"].startswith("helper(")
    assert payload["parent_structural_id"] == repo["ids"]["module_alpha"]
    assert payload["decorators"] == []
    assert "confidence" not in payload


def test_callable_overview_reducer_returns_typescript_metadata(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = callable_overview.run(
        repo["snapshot_id"],
        conn=conn,
        function_id=repo["ids"]["ts_function"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["language"] == "typescript"
    assert payload["parameters"] == ["name"]
    assert payload["decorators"] == []
    assert payload["signature"].startswith("createWidget(name")
    assert "confidence" not in payload


def test_class_overview_reducer_exposes_methods_and_metadata(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = class_overview.run(
        repo["snapshot_id"],
        conn=conn,
        class_id=repo["ids"]["class_order"],
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_qualified_name"] == "pkg.alpha.service"
    assert payload["decorators"] == ["decorator('value')"]
    assert payload["bases"] == ["BaseService", "Mixin"]
    assert payload["methods"] == [
        {
            "function_id": repo["ids"]["method_one"],
            "qualified_name": "pkg.alpha.service.OrderService.method_one",
        }
    ]
    assert "confidence" not in payload


def test_module_overview_reducer_lists_children_and_imports(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = module_overview.run(
        repo["snapshot_id"],
        conn=conn,
        module_id="pkg.alpha.service",
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_structural_id"] == repo["ids"]["module_alpha"]
    assert payload["module_qualified_name"] == "pkg.alpha.service"
    assert payload["files"] == ["pkg/alpha/service.py"]
    assert payload["file_count"] == 1
    assert payload["classes"][0]["qualified_name"] == "pkg.alpha.service.OrderService"
    assert payload["functions"][0]["qualified_name"] == "pkg.alpha.service.helper"
    assert payload["node_counts"] == {"classes": 1, "functions": 1, "methods": 1}
    assert payload["language_breakdown"] == {"python": 3}
    assert payload["imports"] == [
        {
            "module_structural_id": repo["ids"]["module_beta"],
            "module_qualified_name": "pkg.beta.worker",
        }
    ]
    assert "confidence" not in payload


def test_module_overview_reducer_expands_package_modules(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = module_overview.run(
        repo["snapshot_id"],
        conn=conn,
        module_id="pkg.alpha",
        repo_root=repo["repo_root"],
    )
    conn.close()

    assert payload["module_qualified_name"] == "pkg.alpha"
    assert payload["files"] == ["pkg/alpha/__init__.py", "pkg/alpha/service.py"]
    assert payload["file_count"] == 2
    assert payload["classes"][0]["qualified_name"] == "pkg.alpha.service.OrderService"
    assert payload["functions"][0]["qualified_name"] == "pkg.alpha.service.helper"
    assert payload["node_counts"] == {"classes": 1, "functions": 1, "methods": 1}
    assert payload["imports"] == [
        {
            "module_structural_id": repo["ids"]["module_beta"],
            "module_qualified_name": "pkg.beta.worker",
        }
    ]


def test_module_overview_include_file_map(tmp_path):
    repo = _build_profile_repo(tmp_path)
    conn = sqlite3.connect(repo["db_path"])
    conn.row_factory = sqlite3.Row
    payload = module_overview.run(
        repo["snapshot_id"],
        conn=conn,
        module_id="pkg.alpha",
        repo_root=repo["repo_root"],
        include_file_map=True,
    )
    conn.close()

    assert payload["module_file_count"] >= 1
    assert payload["module_files"]
    assert any(
        entry["module_qualified_name"].startswith("pkg.alpha")
        for entry in payload["module_files"]
    )
