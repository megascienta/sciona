# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Class overview reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ...code_analysis.analysis.orderings import order_nodes
from ...code_analysis.tools.profile_introspection import (
    python_class_extras,
    typescript_class_extras,
)
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.profile_utils import fetch_node_instance
from ..helpers import queries
from ..helpers.render import render_json_payload, require_connection
from ..metadata import ReducerMeta
from ..helpers.types import ClassOverviewPayload
from ..helpers.utils import line_span_hash, require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="class_overview",
    category="evidence",
    scope="class",
    placeholders=("CLASS_OVERVIEW",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Structural summary of a class, including methods and metadata. " \
    "Use for quick class inspection. Scope: class-level structure.",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None = None,
    method_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    resolved_class_id = class_id
    repo_path = Path(repo_root) if repo_root else None
    if not resolved_class_id and method_id:
        if repo_path is None:
            raise ValueError(
                "class_overview with method_id requires repo_root for artifact lookup."
            )
        method_structural_id = queries.resolve_method_id(conn, snapshot_id, method_id)
        edges = load_artifact_edges(
            repo_path,
            edge_kinds=["DEFINES_METHOD"],
            dst_ids=[method_structural_id],
        )
        if edges:
            edges.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
            resolved_class_id = edges[0][0]
    payload = run(
        snapshot_id, conn=conn, repo_root=repo_root, class_id=resolved_class_id
    )
    return render_json_payload(payload)


def run(snapshot_id: str, **params) -> ClassOverviewPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError(
            "class_overview reducer requires an active database connection."
        )
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("class_overview reducer requires a committed snapshot.")
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="class_overview reducer"
    )
    class_id = params.get("class_id")
    if not class_id:
        raise ValueError("class_overview requires 'class_id'.")

    row = fetch_node_instance(conn, snapshot_id, class_id)
    if row["node_type"] != "class":
        raise ValueError(f"Node '{class_id}' is not a class.")

    repo_root = params.get("repo_root")
    repo_path = Path(repo_root) if repo_root else None
    module_name = queries.module_id_for_structural(conn, snapshot_id, class_id)
    artifact_available = artifact_db_available(repo_path) if repo_path else False
    decorators: List[str] = []
    bases: List[str] = []
    if row["language"] == "python":
        decorators, bases = python_class_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "typescript":
        decorators, bases = typescript_class_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )

    methods = _load_methods(conn, snapshot_id, class_id, repo_path)
    line_span = [row["start_line"], row["end_line"]]
    return {
        "projection": "class_overview",
        "projection_version": "1.0",
        "class_id": class_id,
        "language": row["language"],
        "module_qualified_name": module_name,
        "file_path": row["file_path"],
        "line_span": line_span,
        "start_byte": row["start_byte"],
        "end_byte": row["end_byte"],
        "content_hash": row["content_hash"],
        "line_span_hash": line_span_hash(repo_path, row["file_path"], line_span),
        "decorators": decorators,
        "bases": bases,
        "methods": methods,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }


def _load_methods(
    conn, snapshot_id: str, class_id: str, repo_root: Path | None
) -> List[Dict[str, str]]:
    if repo_root is None:
        return []
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["DEFINES_METHOD"],
        src_ids=[class_id],
    )
    method_ids = [dst for _, dst, _ in edges]
    if not method_ids:
        return []
    placeholders = ",".join("?" for _ in method_ids)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.structural_id IN ({placeholders})
          AND sn.node_type = 'method'
        """,
        (snapshot_id, *method_ids),
    ).fetchall()
    entries = [
        {"function_id": row["structural_id"], "qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="qualified_name")
    return entries
