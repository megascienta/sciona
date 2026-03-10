# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol lookup reducer."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .helpers.shared.render import render_json_payload, require_connection
from .helpers.shared.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

_NODE_TYPES = {"module", "classifier", "callable"}

REDUCER_META = ReducerMeta(
    reducer_id="symbol_lookup",
    category="structure",
    risk_tier="normal",
    stage="entity_discovery",
    placeholder="SYMBOL_LOOKUP",
    summary="Ranked structural symbol matches for a query. " \
    "Use when resolving unknown identifiers. ",
)

def render(
    snapshot_id: str,
    conn,
    repo_root,
    query: str | None = None,
    kind: str | None = None,
    limit: int | str | None = 10,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="symbol_lookup reducer"
    )
    if not query or not str(query).strip():
        raise ValueError("symbol_lookup requires a non-empty query.")
    node_types = _normalize_kind(kind)
    normalized_query = str(query).strip()
    limit_value = _normalize_limit(limit)
    candidates = _fetch_candidates(
        conn, snapshot_id, normalized_query, node_types, limit=limit_value * 5
    )
    ranked = _rank_candidates(normalized_query, candidates)[:limit_value]
    body = {
        "payload_kind": "summary",
        "query": normalized_query,
        "kind": kind,
        "limit": limit_value,
        "matches": [
            {
                **row,
                "row_origin": "committed",
                "match_status": "active",
            }
            for row in ranked
        ],
    }
    return render_json_payload(body)


def _normalize_kind(kind: Optional[str]) -> Sequence[str]:
    if not kind:
        return tuple(sorted(_NODE_TYPES))
    normalized = str(kind).strip().lower()
    if normalized in {"any", "all"}:
        return tuple(sorted(_NODE_TYPES))
    if normalized == "callable":
        return ("callable",)
    if normalized in {"function", "method"}:
        return ("callable",)
    if normalized == "class":
        return ("classifier",)
    if normalized in _NODE_TYPES:
        return (normalized,)
    raise ValueError(f"Unknown kind '{kind}'.")


def _normalize_limit(limit: int | str | None) -> int:
    if limit is None:
        return 10
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("symbol_lookup limit must be an integer.")
    if value <= 0:
        raise ValueError("symbol_lookup limit must be positive.")
    return min(value, 200)


def _fetch_candidates(
    conn,
    snapshot_id: str,
    query: str,
    node_types: Sequence[str],
    *,
    limit: int,
) -> List[Dict[str, str]]:
    lowered = query.lower()
    placeholders = ", ".join("?" for _ in node_types)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
          AND (sn.structural_id = ? OR LOWER(ni.qualified_name) LIKE ?)
        ORDER BY ni.qualified_name, ni.file_path, sn.structural_id
        LIMIT ?
        """,
        (snapshot_id, *node_types, query, f"%{lowered}%", limit),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "node_type": row["node_type"],
            "language": row["language"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
        if row["qualified_name"]
    ]


def _rank_candidates(
    query: str, candidates: List[Dict[str, str]]
) -> List[Dict[str, object]]:
    lowered = query.lower()
    ranked: List[Dict[str, object]] = []
    for row in candidates:
        qualified_name = str(row["qualified_name"])
        score = _score_identifier(lowered, qualified_name.lower(), row["structural_id"])
        ranked.append({**row, "score": score})
    ranked.sort(
        key=lambda item: (
            -float(item["score"]),
            str(item["qualified_name"]),
            str(item["file_path"]),
        )
    )
    return ranked


def _score_identifier(
    identifier: str, qualified_name: str, structural_id: str
) -> float:
    if identifier == structural_id:
        return 1.0
    if identifier == qualified_name:
        return 1.0
    if qualified_name.startswith(identifier):
        return 0.9
    if qualified_name.endswith(identifier):
        return 0.8
    if f".{identifier}" in qualified_name:
        return 0.75
    if identifier in qualified_name:
        return 0.6
    return 0.5
