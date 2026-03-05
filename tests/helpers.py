# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sciona.runtime import constants as setup_config
from sciona.runtime import paths as runtime_paths
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.maintenance import rebuild_graph_index
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.data_storage.transactions import transaction
from sciona.pipelines import setup as versioning


def insert_snapshot(
    conn,
    snapshot_id: str,
    *,
    is_committed: bool = True,
    structural_hash: Optional[str] = None,
) -> None:
    created_at = "2024-01-01T00:00:00Z"
    commit_time = created_at
    structural_hash = structural_hash or f"hash-{snapshot_id}"
    conn.execute(
        """
        INSERT INTO snapshots(
            snapshot_id,
            created_at,
            source,
            is_committed,
            structural_hash,
            git_commit_sha,
            git_commit_time,
            git_branch
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            created_at,
            "test",
            1 if is_committed else 0,
            structural_hash,
            f"commit-{snapshot_id}",
            commit_time,
            "main",
        ),
    )


def strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed


def parse_json_payload(text: str) -> dict:
    import json

    return json.loads(strip_json_fence(text))


def core_conn(repo_root: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    return conn


def qualify_repo_name(repo_root: Path, name: str) -> str:
    return f"{runtime_paths.repo_name_prefix(repo_root)}.{name}"


def setup_structural_index_db(tmp_path: Path, *, repo_root: Path) -> Tuple[Path, str]:
    """Create a minimal database with one snapshot and module structure."""
    db_path = tmp_path / "structural_index.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    snapshot_id = "snap_state"
    insert_snapshot(conn, snapshot_id, structural_hash="struct-state")
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    def _q(name: str) -> str:
        return f"{repo_prefix}.{name}"
    nodes = [
        ("mod_alpha", "module", "python", _q("pkg.alpha"), "pkg/alpha/__init__.py"),
        ("mod_beta", "module", "python", _q("pkg.beta"), "pkg/beta/__init__.py"),
        ("cls_alpha", "type", "python", _q("pkg.alpha.Service"), "pkg/alpha/service.py"),
        (
            "func_alpha",
            "callable",
            "python",
            _q("pkg.alpha.service.helper"),
            "pkg/alpha/service.py",
        ),
        (
            "meth_alpha",
            "callable",
            "python",
            _q("pkg.alpha.Service.run"),
            "pkg/alpha/service.py",
        ),
    ]
    for structural_id, node_type, language, qualified_name, path in nodes:
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
                path,
                1,
                10,
                f"hash-{structural_id}",
            ),
        )
    edges = [
        (snapshot_id, "mod_alpha", "cls_alpha", "LEXICALLY_CONTAINS"),
        (snapshot_id, "mod_alpha", "func_alpha", "LEXICALLY_CONTAINS"),
        (snapshot_id, "cls_alpha", "meth_alpha", "LEXICALLY_CONTAINS"),
        (snapshot_id, "mod_alpha", "mod_beta", "IMPORTS_DECLARED"),
        (snapshot_id, "mod_beta", "mod_alpha", "IMPORTS_DECLARED"),
    ]
    for snap, src, dst, edge_type in edges:
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snap, src, dst, edge_type),
        )
    conn.commit()
    conn.close()
    return db_path, snapshot_id


def seed_repo_with_snapshot(tmp_path: Path, *, commit: bool = True) -> Tuple[Path, str]:
    """Helper that materializes a repo with a snapshot database and basic files."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root)
    db_path, snapshot_id = setup_structural_index_db(tmp_path, repo_root=repo_root)
    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir()
    shutil.copy(db_path, sciona_dir / "sciona.db")
    versioning.write_version_file(sciona_dir)
    core_conn = sqlite3.connect(sciona_dir / "sciona.db")
    core_conn.row_factory = sqlite3.Row
    artifact_conn = artifact_connect(sciona_dir / setup_config.ARTIFACT_DB_FILENAME)
    try:
        with transaction(artifact_conn):
            rebuild_graph_index(
                artifact_conn,
                core_conn=core_conn,
                snapshot_id=snapshot_id,
            )
    finally:
        artifact_conn.close()
        core_conn.close()
    (repo_root / "pkg/alpha").mkdir(parents=True, exist_ok=True)
    (repo_root / "pkg/beta").mkdir(parents=True, exist_ok=True)
    (repo_root / "pkg/alpha/service.py").write_text(
        "def helper():\n    return 1\n", encoding="utf-8"
    )
    (repo_root / "pkg/alpha/__init__.py").write_text("", encoding="utf-8")
    (repo_root / "pkg/beta/__init__.py").write_text("", encoding="utf-8")
    if commit:
        commit_all(repo_root)
    return repo_root, snapshot_id


def init_git_repo(repo_root: Path, *, commit: bool = False) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    if commit:
        subprocess.run(
            ["git", "add", "-A"], cwd=repo_root, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )


def commit_all(repo_root: Path, *, message: str = "init") -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message], cwd=repo_root, check=True, capture_output=True
    )


def write_and_commit_file(
    repo_root: Path, relative_path: str | Path, content: str, *, message: str
) -> None:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(
        ["git", "add", str(relative_path)],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


def setup_evolution_db(tmp_path: Path) -> Dict[str, object]:
    """Create a database with two snapshots used by change_delta/impact_preview tests."""
    db_path = tmp_path / "evolution.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    insert_snapshot(
        conn, "snap_a", is_committed=False, structural_hash="struct-a"
    )
    insert_snapshot(conn, "snap_b", structural_hash="struct-b")
    nodes = [
        (
            "mod_alpha",
            "module",
            "python",
            "pkg.alpha",
            "pkg/alpha/__init__.py",
            ["snap_a", "snap_b"],
        ),
        (
            "mod_beta",
            "module",
            "python",
            "pkg.beta",
            "pkg/beta/__init__.py",
            ["snap_b"],
        ),
        (
            "func_old",
            "callable",
            "python",
            "pkg.alpha.old_helper",
            "pkg/alpha/old.py",
            ["snap_a"],
        ),
        (
            "func_new",
            "callable",
            "python",
            "pkg.alpha.new_helper",
            "pkg/alpha/new.py",
            ["snap_b"],
        ),
        (
            "func_beta",
            "callable",
            "python",
            "pkg.beta.worker",
            "pkg/beta/worker.py",
            ["snap_a", "snap_b"],
        ),
        (
            "orphan_func",
            "callable",
            "python",
            "pkg.alpha.orphan",
            "pkg/alpha/orphan.py",
            ["snap_b"],
        ),
    ]
    for (
        structural_id,
        node_type,
        language,
        qualified_name,
        path,
        snapshots_present,
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
                "snap_a",
            ),
        )
        for snap in snapshots_present:
            conn.execute(
                """
                INSERT INTO node_instances(
                    instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{snap}:{structural_id}",
                    structural_id,
                    snap,
                    qualified_name,
                    path,
                    1,
                    5,
                    f"hash-{structural_id}-{snap}",
                ),
            )
    edges = [
        ("snap_a", "mod_alpha", "func_old", "LEXICALLY_CONTAINS"),
        ("snap_a", "mod_alpha", "func_beta", "LEXICALLY_CONTAINS"),
        ("snap_b", "mod_alpha", "func_new", "LEXICALLY_CONTAINS"),
        ("snap_b", "mod_beta", "func_beta", "LEXICALLY_CONTAINS"),
        ("snap_b", "mod_alpha", "mod_beta", "IMPORTS_DECLARED"),
    ]
    for snap, src, dst, edge_type in edges:
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snap, src, dst, edge_type),
        )
    conn.commit()
    conn.close()
    return {
        "db_path": db_path,
        "snapshot_a": "snap_a",
        "snapshot_b": "snap_b",
    }


@dataclass
class DiagnosticsResult:
    health: str
    metrics: Dict[str, object]


class Diagnostics:
    """Evaluate SCI integrity for a snapshot (test-only helper)."""

    def __init__(self, conn):
        self._conn = conn

    def run(
        self, snapshot_id: str, include_breakdown: bool = False
    ) -> DiagnosticsResult:
        orphan_nodes = self._find_orphan_nodes(snapshot_id)
        dangling_edges = self._count_dangling_edges(snapshot_id)
        missing_instances = self._count_missing_instances(snapshot_id)
        containment_conflicts = self._find_containment_conflicts(snapshot_id)
        low_conf_ratio, low_conf_count = self._low_confidence_nodes(snapshot_id)

        metrics: Dict[str, object] = {
            "orphan_nodes": {
                "count": len(orphan_nodes),
                "structural_ids": orphan_nodes,
            },
            "dangling_edges": dangling_edges,
            "missing_instances": missing_instances,
            "containment_conflicts": {
                "count": len(containment_conflicts),
                "structural_ids": containment_conflicts,
            },
            "low_confidence_nodes": {
                "count": low_conf_count,
                "ratio": low_conf_ratio,
                "threshold": 0.35,
            },
        }
        if include_breakdown:
            metrics["module_breakdown"] = self._module_breakdown(
                snapshot_id,
                orphan_nodes,
                containment_conflicts,
            )

        degraded = (
            metrics["orphan_nodes"]["count"] > 0  # type: ignore[index]
            or metrics["dangling_edges"] > 0  # type: ignore[operator]
            or metrics["missing_instances"] > 0  # type: ignore[operator]
            or metrics["containment_conflicts"]["count"] > 0  # type: ignore[index]
            or low_conf_ratio > 0.35
        )
        health = "degraded" if degraded else "ok"
        return DiagnosticsResult(health=health, metrics=metrics)

    def _find_orphan_nodes(self, snapshot_id: str) -> List[str]:
        rows = self._conn.execute(
            """
            SELECT ni.structural_id
            FROM node_instances ni
            JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
            LEFT JOIN edges e
                ON e.snapshot_id = ni.snapshot_id
               AND e.dst_structural_id = ni.structural_id
               AND e.edge_type IN ('LEXICALLY_CONTAINS', 'LEXICALLY_CONTAINS')
            WHERE ni.snapshot_id = ?
              AND sn.node_type IN ('type', 'callable', 'callable')
            GROUP BY ni.structural_id
            HAVING COUNT(e.dst_structural_id) = 0
            """,
            (snapshot_id,),
        ).fetchall()
        structural_ids = [row["structural_id"] for row in rows]
        structural_ids.sort()
        return structural_ids

    def _count_dangling_edges(self, snapshot_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM edges e
            LEFT JOIN node_instances src
                ON src.structural_id = e.src_structural_id
               AND src.snapshot_id = e.snapshot_id
            LEFT JOIN node_instances dst
                ON dst.structural_id = e.dst_structural_id
               AND dst.snapshot_id = e.snapshot_id
            WHERE e.snapshot_id = ?
              AND (src.structural_id IS NULL OR dst.structural_id IS NULL)
            """,
            (snapshot_id,),
        ).fetchone()
        return row["count"] if row else 0

    def _count_missing_instances(self, snapshot_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM structural_nodes sn
            WHERE sn.structural_id NOT IN (
                SELECT structural_id FROM node_instances WHERE snapshot_id = ?
            )
            """,
            (snapshot_id,),
        ).fetchone()
        return row["count"] if row else 0

    def _find_containment_conflicts(self, snapshot_id: str) -> List[str]:
        rows = self._conn.execute(
            """
            SELECT e.dst_structural_id AS structural_id
            FROM edges e
            WHERE e.snapshot_id = ?
              AND e.edge_type IN ('LEXICALLY_CONTAINS', 'LEXICALLY_CONTAINS')
            GROUP BY e.dst_structural_id
            HAVING COUNT(*) > 1
            """,
            (snapshot_id,),
        ).fetchall()
        structural_ids = [row["structural_id"] for row in rows]
        structural_ids.sort()
        return structural_ids

    def _low_confidence_nodes(self, snapshot_id: str) -> Tuple[float, int]:
        return 0.0, 0

    def _module_breakdown(
        self,
        snapshot_id: str,
        orphan_nodes: List[str],
        containment_conflicts: List[str],
    ) -> List[Dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT sn.structural_id, sn.node_type, ni.qualified_name
            FROM structural_nodes sn
            JOIN node_instances ni ON ni.structural_id = sn.structural_id
            WHERE ni.snapshot_id = ?
            """,
            (snapshot_id,),
        ).fetchall()
        module_names = {
            row["qualified_name"]
            for row in rows
            if row["node_type"] == "module" and row["qualified_name"]
        }
        lookup = {}
        for row in rows:
            qualified_name = row["qualified_name"]
            if not qualified_name:
                continue
            lookup[row["structural_id"]] = _module_id_for(qualified_name, module_names)
        issues: Dict[str, Dict[str, int]] = {}
        for structural_id in orphan_nodes:
            module_id = lookup.get(structural_id)
            if not module_id:
                continue
            entry = issues.setdefault(
                module_id,
                {"module_id": module_id, "orphan_nodes": 0, "containment_conflicts": 0},
            )
            entry["orphan_nodes"] += 1
        for structural_id in containment_conflicts:
            module_id = lookup.get(structural_id)
            if not module_id:
                continue
            entry = issues.setdefault(
                module_id,
                {"module_id": module_id, "orphan_nodes": 0, "containment_conflicts": 0},
            )
            entry["containment_conflicts"] += 1
        entries = list(issues.values())
        entries.sort(
            key=lambda item: (
                -(item["orphan_nodes"] + item["containment_conflicts"]),
                item["module_id"],
            )
        )
        return entries


@dataclass(frozen=True)
class SnapshotDelta:
    """Precomputed structural delta between two snapshots (test-only helper)."""

    snapshot_a: str
    snapshot_b: str
    added_nodes: List[Dict[str, object]]
    removed_nodes: List[Dict[str, object]]
    moved_nodes: List[Dict[str, object]]
    added_edges: List[Dict[str, object]]
    removed_edges: List[Dict[str, object]]
    identity_transitions: List[Dict[str, object]]
    file_transitions: List[Dict[str, object]]

    @classmethod
    def compute(cls, conn, snapshot_a: str, snapshot_b: str) -> "SnapshotDelta":
        if not snapshot_a or not snapshot_b:
            raise ValueError("SnapshotDelta requires both snapshot_a and snapshot_b.")

        nodes_a = _load_nodes(conn, snapshot_a)
        nodes_b = _load_nodes(conn, snapshot_b)
        edges_a = _load_edges(conn, snapshot_a)
        edges_b = _load_edges(conn, snapshot_b)

        added_nodes = [
            _node_entry(structural_id, nodes_b[structural_id])  # type: ignore[index]
            for structural_id in sorted(set(nodes_b) - set(nodes_a))
        ]
        removed_nodes = [
            _node_entry(structural_id, nodes_a[structural_id])  # type: ignore[index]
            for structural_id in sorted(set(nodes_a) - set(nodes_b))
        ]
        moved_nodes = [
            {
                "structural_id": structural_id,
                "qualified_name": nodes_b[structural_id]["qualified_name"],
                "from_path": nodes_a[structural_id]["file_path"],
                "to_path": nodes_b[structural_id]["file_path"],
            }
            for structural_id in sorted(set(nodes_a) & set(nodes_b))
            if nodes_a[structural_id]["file_path"]
            != nodes_b[structural_id]["file_path"]
        ]
        added_nodes.sort(key=lambda item: item.get("qualified_name") or "")
        removed_nodes.sort(key=lambda item: item.get("qualified_name") or "")
        moved_nodes.sort(key=lambda item: item.get("qualified_name") or "")

        added_edges = [_edge_entry(edge) for edge in edges_b - edges_a]
        removed_edges = [_edge_entry(edge) for edge in edges_a - edges_b]
        added_edges.sort(
            key=lambda item: (
                item["src_structural_id"],
                item["dst_structural_id"],
                item["edge_type"],
            )
        )
        removed_edges.sort(
            key=lambda item: (
                item["src_structural_id"],
                item["dst_structural_id"],
                item["edge_type"],
            )
        )

        return cls(
            snapshot_a=snapshot_a,
            snapshot_b=snapshot_b,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            moved_nodes=moved_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            identity_transitions=[],
            file_transitions=[],
        )


def _load_nodes(conn, snapshot_id: str) -> Dict[str, Dict[str, object]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return {
        row["structural_id"]: {
            "node_type": row["node_type"],
            "language": row["language"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    }


def _load_edges(conn, snapshot_id: str) -> set[Tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT src_structural_id, dst_structural_id, edge_type
        FROM edges
        WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return {
        (row["src_structural_id"], row["dst_structural_id"], row["edge_type"])
        for row in rows
    }


def _node_entry(structural_id: str, data: Dict[str, object]) -> Dict[str, object]:
    return {
        "structural_id": structural_id,
        "qualified_name": data.get("qualified_name"),
        "node_type": data.get("node_type"),
        "language": data.get("language"),
        "file_path": data.get("file_path"),
    }


def _edge_entry(edge_id: Tuple[str, str, str]) -> Dict[str, object]:
    src, dst, edge_type = edge_id
    return {
        "src_structural_id": src,
        "dst_structural_id": dst,
        "edge_type": edge_type,
    }


def _module_id_for(qualified_name: str, module_names: set[str]) -> str:
    if not qualified_name:
        return ""
    if qualified_name in module_names:
        return qualified_name
    parts = qualified_name.split(".")
    for end in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:end])
        if candidate in module_names:
            return candidate
    return parts[0]
