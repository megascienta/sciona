# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Classifier relationships reducer."""

from __future__ import annotations

from pathlib import Path

from .helpers import queries
from . import classifier_overview
from .helpers.artifact_graph_edges import load_artifact_edges
from .helpers.render import render_json_payload, require_connection
from .helpers.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="classifier_inheritance",
    category="structure",
    risk_tier="normal",
    stage="structure_inspection",
    placeholder="CLASSIFIER_INHERITANCE",
    summary="Parsed base classifiers and inheritance relations. " \
    "Use when reasoning about classifier hierarchy or polymorphic structure. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    classifier_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="classifier_inheritance reducer"
    )
    resolved_id = queries.resolve_classifier_id(conn, snapshot_id, classifier_id)
    outgoing = _load_classifier_edges(
        conn=conn,
        snapshot_id=snapshot_id,
        repo_root=repo_root,
        classifier_id=resolved_id,
        direction="outgoing",
    )
    incoming = _load_classifier_edges(
        conn=conn,
        snapshot_id=snapshot_id,
        repo_root=repo_root,
        classifier_id=resolved_id,
        direction="incoming",
    )
    edge_source = "sci" if (outgoing or incoming) else "none"
    if not outgoing and not incoming:
        overview = classifier_overview.run(
            snapshot_id, conn=conn, repo_root=repo_root, classifier_id=resolved_id
        )
        bases = overview.get("bases") or []
        outgoing = [
            {
                "edge_type": "INHERITS",
                "related_structural_id": None,
                "related_qualified_name": base,
            }
            for base in bases
        ]
        outgoing.sort(key=lambda item: str(item.get("related_qualified_name") or ""))
        edge_source = "profile" if bases else "none"
    body = {
        "payload_kind": "summary",
        "classifier_id": resolved_id,
        "outgoing_count": len(outgoing),
        "incoming_count": len(incoming),
        "outgoing": outgoing,
        "incoming": incoming,
        "edge_source": edge_source,
    }
    return render_json_payload(body)


def _load_classifier_edges(
    *,
    conn,
    snapshot_id: str,
    repo_root,
    classifier_id: str,
    direction: str,
) -> list[dict[str, str | None]]:
    if not repo_root:
        return []
    if direction not in {"outgoing", "incoming"}:
        raise ValueError("direction must be outgoing or incoming.")
    repo_path = Path(repo_root)
    if direction == "outgoing":
        edges = load_artifact_edges(
            repo_path, edge_kinds=["EXTENDS", "IMPLEMENTS"], src_ids=[classifier_id]
        )
        target_ids = [dst_id for _src_id, dst_id, _edge_kind in edges]
    else:
        edges = load_artifact_edges(
            repo_path, edge_kinds=["EXTENDS", "IMPLEMENTS"], dst_ids=[classifier_id]
        )
        target_ids = [src_id for src_id, _dst_id, _edge_kind in edges]
    if not edges:
        return []
    lookup = _node_lookup(conn, snapshot_id=snapshot_id, structural_ids=target_ids)
    entries: list[dict[str, str | None]] = []
    for src_id, dst_id, edge_kind in edges:
        related_id = dst_id if direction == "outgoing" else src_id
        node = lookup.get(related_id) or {}
        entries.append(
            {
                "edge_type": edge_kind,
                "related_structural_id": related_id,
                "related_qualified_name": node.get("qualified_name"),
            }
        )
    entries.sort(
        key=lambda item: (
            str(item.get("edge_type") or ""),
            str(item.get("related_qualified_name") or ""),
            str(item.get("related_structural_id") or ""),
        )
    )
    return entries


def _node_lookup(
    conn,
    *,
    snapshot_id: str,
    structural_ids: list[str],
) -> dict[str, dict[str, str]]:
    if not structural_ids:
        return {}
    placeholders = ",".join("?" for _ in structural_ids)
    rows = conn.execute(
        f"""
        SELECT ni.structural_id, ni.qualified_name
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.structural_id IN ({placeholders})
        """,
        (snapshot_id, *structural_ids),
    ).fetchall()
    return {
        row["structural_id"]: {"qualified_name": row["qualified_name"]}
        for row in rows
        if row["qualified_name"]
    }
