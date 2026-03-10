# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Classifier overview reducer."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..code_analysis.analysis.orderings import order_nodes
from ..code_analysis.tools.profiling import (
    java_class_extras,
    javascript_class_extras,
    python_class_extras,
    typescript_class_extras,
)
from .helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from .helpers.shared.profile_utils import fetch_node_instance
from .helpers.shared import queries
from .helpers.shared.render import render_json_payload, require_connection
from .metadata import ReducerMeta
from .helpers.shared.types import ClassifierOverviewPayload
from .helpers.shared.utils import line_span_hash, require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="classifier_overview",
    category="structure",
    risk_tier="normal",
    stage="structure_inspection",
    placeholder="CLASSIFIER_OVERVIEW",
    summary="Structural summary of a classifier, including methods and metadata. " \
    "Use for quick classifier inspection.",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    classifier_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    payload = run(
        snapshot_id, conn=conn, repo_root=repo_root, classifier_id=classifier_id
    )
    return render_json_payload(payload)


def run(snapshot_id: str, **params) -> ClassifierOverviewPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError(
            "classifier_overview reducer requires an active database connection."
        )
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("classifier_overview reducer requires a committed snapshot.")
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="classifier_overview reducer"
    )
    classifier_id = params.get("classifier_id")
    if not classifier_id:
        raise ValueError("classifier_overview requires 'classifier_id'.")

    row = fetch_node_instance(conn, snapshot_id, classifier_id)
    if row["node_type"] != "classifier":
        raise ValueError(f"Node '{classifier_id}' is not a classifier.")

    repo_root = params.get("repo_root")
    repo_path = Path(repo_root) if repo_root else None
    module_name = queries.module_id_for_structural(conn, snapshot_id, classifier_id)
    artifact_available = artifact_db_available(repo_path) if repo_path else False
    bases: List[str] = []
    if row["language"] == "python":
        bases = python_class_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "typescript":
        bases = typescript_class_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "javascript":
        bases = javascript_class_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )
    elif row["language"] == "java":
        bases = java_class_extras(
            row["language"],
            repo_path,
            row["file_path"],
            row["start_line"],
            row["end_line"],
        )

    methods = _load_methods(conn, snapshot_id, classifier_id, repo_path)
    line_span = [row["start_line"], row["end_line"]]
    return {
        "projection": "classifier_overview",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "classifier_id": classifier_id,
        "language": row["language"],
        "module_qualified_name": module_name,
        "file_path": row["file_path"],
        "line_span": line_span,
        "start_byte": row["start_byte"],
        "end_byte": row["end_byte"],
        "content_hash": row["content_hash"],
        "line_span_hash": line_span_hash(repo_path, row["file_path"], line_span),
        "bases": bases,
        "methods": methods,
        "artifact_available": artifact_available,
        "edge_source": "artifact_db" if artifact_available else "none",
    }


def _load_methods(
    conn, snapshot_id: str, classifier_id: str, repo_root: Path | None
) -> List[Dict[str, str]]:
    if repo_root is None:
        return []
    edges = load_artifact_edges(
        repo_root,
        edge_kinds=["LEXICALLY_CONTAINS"],
        src_ids=[classifier_id],
    )
    callable_ids = [dst for _, dst, _ in edges]
    if not callable_ids:
        return []
    placeholders = ",".join("?" for _ in callable_ids)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.structural_id IN ({placeholders})
          AND sn.node_type = 'callable'
        """,
        (snapshot_id, *callable_ids),
    ).fetchall()
    entries = [
        {"callable_id": row["structural_id"], "qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    ]
    order_nodes(entries, key="qualified_name")
    return entries
