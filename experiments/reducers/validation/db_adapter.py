# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict, List, Optional

from sciona.api import addons as sciona_api
from sciona.reducers.core import module_overview

from .independent.shared import EdgeRecord


def resolve_node_instance(
    conn,
    snapshot_id: str,
    qualified_name: str,
    node_type: str,
) -> Optional[dict]:
    row = conn.execute(
        """
        SELECT ni.structural_id,
               ni.file_path,
               ni.start_line,
               ni.end_line,
               sn.language,
               sn.node_type
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.qualified_name = ?
          AND sn.node_type = ?
        """,
        (snapshot_id, qualified_name, node_type),
    ).fetchone()
    if not row:
        return None
    return {
        "structural_id": row["structural_id"],
        "file_path": row["file_path"],
        "start_line": row["start_line"],
        "end_line": row["end_line"],
        "language": row["language"],
        "node_type": row["node_type"],
    }


def module_import_edges(
    core_conn,
    snapshot_id: str,
    module_structural_id: str,
) -> List[EdgeRecord]:
    return module_import_edges_for_ids(core_conn, snapshot_id, [module_structural_id])


def module_import_edges_for_ids(
    core_conn,
    snapshot_id: str,
    module_structural_ids: List[str],
) -> List[EdgeRecord]:
    if not module_structural_ids:
        return []
    placeholders = ",".join("?" for _ in module_structural_ids)
    rows = core_conn.execute(
        f"""
        SELECT e.src_structural_id, e.dst_structural_id
        FROM edges e
        WHERE e.snapshot_id = ?
          AND e.edge_type = 'IMPORTS_DECLARED'
          AND e.src_structural_id IN ({placeholders})
        """,
        (snapshot_id, *module_structural_ids),
    ).fetchall()
    node_ids = {row["src_structural_id"] for row in rows} | {
        row["dst_structural_id"] for row in rows
    }
    lookup = node_lookup(core_conn, snapshot_id, node_ids)
    edges: List[EdgeRecord] = []
    for row in rows:
        src_name = lookup.get(row["src_structural_id"], "")
        dst_name = lookup.get(row["dst_structural_id"], "")
        edges.append(
            EdgeRecord(
                caller=src_name,
                callee=dst_name,
                callee_qname=dst_name,
            )
        )
    return edges


def callable_call_edges(
    artifact_conn,
    core_conn,
    snapshot_id: str,
    callable_structural_id: str,
) -> List[EdgeRecord]:
    if artifact_conn is None:
        return []
    rows = artifact_conn.execute(
        """
        SELECT src_node_id, dst_node_id
        FROM graph_edges
        WHERE edge_kind = 'CALLS'
          AND src_node_id = ?
        """,
        (callable_structural_id,),
    ).fetchall()
    node_ids = {row["src_node_id"] for row in rows} | {
        row["dst_node_id"] for row in rows
    }
    lookup = node_lookup(core_conn, snapshot_id, node_ids)
    edges: List[EdgeRecord] = []
    for row in rows:
        src_name = lookup.get(row["src_node_id"], "")
        dst_name = lookup.get(row["dst_node_id"], "")
        edges.append(
            EdgeRecord(
                caller=src_name,
                callee=dst_name.split(".")[-1] if dst_name else "",
                callee_qname=dst_name or None,
            )
        )
    return edges


def class_method_ids(artifact_conn, class_structural_id: str) -> List[str]:
    if artifact_conn is None:
        return []
    rows = artifact_conn.execute(
        """
        SELECT dst_node_id
        FROM graph_edges
        WHERE edge_kind = 'DEFINES_METHOD'
          AND src_node_id = ?
        """,
        (class_structural_id,),
    ).fetchall()
    return [row["dst_node_id"] for row in rows]


def node_lookup(core_conn, snapshot_id: str, structural_ids: set[str]) -> Dict[str, str]:
    if not structural_ids:
        return {}
    placeholders = ",".join("?" for _ in structural_ids)
    rows = core_conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.structural_id IN ({placeholders})
        """,
        (snapshot_id, *structural_ids),
    ).fetchall()
    return {row["structural_id"]: row["qualified_name"] for row in rows if row["qualified_name"]}


def resolve_module_structural_ids(
    core_conn,
    snapshot_id: str,
    module_name: str,
) -> List[str]:
    return module_overview._resolve_module_ids(core_conn, snapshot_id, module_name)


def open_core_db(repo_root):
    return sciona_api.core_readonly(repo_root)


def open_artifact_db(repo_root):
    return sciona_api.artifact_readonly(repo_root)
