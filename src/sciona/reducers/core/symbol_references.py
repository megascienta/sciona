# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol reference reducer."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

_NODE_TYPES = {"module", "class", "function", "method"}

REDUCER_META = ReducerMeta(
    reducer_id="symbol_references",
    category="core",
    scope="codebase",
    placeholders=("SYMBOL_REFERENCES",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Structural relationships (calls/imports) for matched symbols. " \
    "Use for impact analysis or dependency tracing. " \
    "Scope: symbol → relations. Payload kind: summary.",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    query: str | None = None,
    kind: str | None = None,
    limit: int | str | None = 20,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="symbol_references reducer"
    )
    if not query or not str(query).strip():
        raise ValueError("symbol_references requires a non-empty query.")
    node_types = _normalize_kind(kind)
    normalized_query = str(query).strip()
    limit_value = _normalize_limit(limit)
    candidates = _fetch_candidates(
        conn, snapshot_id, normalized_query, node_types, limit=limit_value * 5
    )
    ranked = _rank_candidates(normalized_query, candidates)[:limit_value]
    node_ids = [match["structural_id"] for match in ranked]
    lookup = _node_lookup(conn, snapshot_id, set(node_ids))
    references = _build_references(conn, repo_root, snapshot_id, ranked, lookup)
    artifact_available = artifact_db_available(repo_root) if repo_root else False
    body = {
        "payload_kind": "summary",
        "query": normalized_query,
        "kind": kind,
        "limit": limit_value,
        "matches": ranked,
        "reference_count": len(references),
        "references": references,
        "artifact_available": artifact_available,
        "call_edge_source": "artifact_db" if artifact_available else "none",
        "import_edge_source": "sci",
    }
    return render_json_payload(body)


def _normalize_kind(kind: Optional[str]) -> Sequence[str]:
    if not kind:
        return tuple(sorted(_NODE_TYPES))
    normalized = str(kind).strip().lower()
    if normalized in {"any", "all"}:
        return tuple(sorted(_NODE_TYPES))
    if normalized == "callable":
        return ("function", "method")
    if normalized in _NODE_TYPES:
        return (normalized,)
    raise ValueError(f"Unknown kind '{kind}'.")


def _normalize_limit(limit: int | str | None) -> int:
    if limit is None:
        return 20
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("symbol_references limit must be an integer.")
    if value <= 0:
        raise ValueError("symbol_references limit must be positive.")
    return min(value, 200)


def _fetch_candidates(
    conn,
    snapshot_id: str,
    query: str,
    node_types: Sequence[str],
    *,
    limit: int,
) -> List[Dict[str, object]]:
    lowered = query.lower()
    placeholders = ", ".join("?" for _ in node_types)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
          AND (sn.structural_id = ? OR LOWER(ni.qualified_name) LIKE ?)
        ORDER BY ni.qualified_name
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
            "line_span": [row["start_line"], row["end_line"]],
        }
        for row in rows
        if row["qualified_name"]
    ]


def _rank_candidates(
    query: str, candidates: List[Dict[str, object]]
) -> List[Dict[str, object]]:
    lowered = query.lower()
    ranked: List[Dict[str, object]] = []
    for row in candidates:
        qualified_name = str(row["qualified_name"])
        score = _score_identifier(
            lowered, qualified_name.lower(), str(row["structural_id"])
        )
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


def _build_references(
    conn,
    repo_root,
    snapshot_id: str,
    matches: List[Dict[str, object]],
    lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    callable_ids = [
        match["structural_id"]
        for match in matches
        if match["node_type"] in {"function", "method"}
    ]
    module_ids = [
        match["structural_id"] for match in matches if match["node_type"] == "module"
    ]
    references: List[Dict[str, object]] = []
    if callable_ids:
        references.extend(
            _call_references(conn, repo_root, snapshot_id, callable_ids, lookup)
        )
    if module_ids:
        references.extend(_import_references(conn, snapshot_id, module_ids, lookup))
    references.sort(
        key=lambda item: (
            str(item.get("symbol_id")),
            str(item.get("reference_kind")),
            str(item.get("direction")),
            str(item.get("edge_kind")),
            str(item.get("other_id")),
        )
    )
    return references


def _call_references(
    conn,
    repo_root,
    snapshot_id: str,
    callable_ids: List[str],
    lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    if repo_root is None:
        return []
    outgoing = load_artifact_edges(
        repo_root,
        edge_kinds=["CALLS"],
        src_ids=callable_ids,
    )
    incoming = load_artifact_edges(
        repo_root,
        edge_kinds=["CALLS"],
        dst_ids=callable_ids,
    )
    refs: List[Dict[str, object]] = []
    all_ids = (
        {src for src, _, _ in outgoing}
        | {dst for _, dst, _ in outgoing}
        | {src for src, _, _ in incoming}
        | {dst for _, dst, _ in incoming}
    )
    lookup = {**lookup, **_node_lookup(conn, snapshot_id, set(all_ids))}
    for src, dst, edge_kind in outgoing:
        other = lookup.get(dst, {})
        refs.append(
            {
                "symbol_id": src,
                "reference_kind": "call",
                "direction": "out",
                "edge_kind": edge_kind,
                "other_id": dst,
                "other_qualified_name": other.get("qualified_name"),
                "other_node_type": other.get("node_type"),
                "other_file_path": other.get("file_path"),
            }
        )
    for src, dst, edge_kind in incoming:
        other = lookup.get(src, {})
        refs.append(
            {
                "symbol_id": dst,
                "reference_kind": "call",
                "direction": "in",
                "edge_kind": edge_kind,
                "other_id": src,
                "other_qualified_name": other.get("qualified_name"),
                "other_node_type": other.get("node_type"),
                "other_file_path": other.get("file_path"),
            }
        )
    return refs


def _import_references(
    conn,
    snapshot_id: str,
    module_ids: List[str],
    lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, object]]:
    if not module_ids:
        return []
    placeholders = ",".join("?" for _ in module_ids)
    rows = conn.execute(
        f"""
        SELECT e.src_structural_id,
               e.dst_structural_id,
               e.edge_type
        FROM edges e
        WHERE e.snapshot_id = ?
          AND e.edge_type = 'IMPORTS_DECLARED'
          AND (e.src_structural_id IN ({placeholders}) OR e.dst_structural_id IN ({placeholders}))
        ORDER BY e.src_structural_id, e.dst_structural_id
        """,
        (snapshot_id, *module_ids, *module_ids),
    ).fetchall()
    refs: List[Dict[str, object]] = []
    all_ids = {row["src_structural_id"] for row in rows} | {
        row["dst_structural_id"] for row in rows
    }
    lookup = {**lookup, **_node_lookup(conn, snapshot_id, set(all_ids))}
    for row in rows:
        src = row["src_structural_id"]
        dst = row["dst_structural_id"]
        edge_kind = row["edge_type"]
        if src in module_ids:
            other = lookup.get(dst, {})
            refs.append(
                {
                    "symbol_id": src,
                    "reference_kind": "import",
                    "direction": "out",
                    "edge_kind": edge_kind,
                    "other_id": dst,
                    "other_qualified_name": other.get("qualified_name"),
                    "other_node_type": other.get("node_type"),
                    "other_file_path": other.get("file_path"),
                }
            )
        if dst in module_ids:
            other = lookup.get(src, {})
            refs.append(
                {
                    "symbol_id": dst,
                    "reference_kind": "import",
                    "direction": "in",
                    "edge_kind": edge_kind,
                    "other_id": src,
                    "other_qualified_name": other.get("qualified_name"),
                    "other_node_type": other.get("node_type"),
                    "other_file_path": other.get("file_path"),
                }
            )
    return refs


def _node_lookup(
    conn, snapshot_id: str, node_ids: set[str]
) -> Dict[str, Dict[str, str]]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
            AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *node_ids),
    ).fetchall()
    return {
        row["structural_id"]: {
            "node_type": row["node_type"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
        if row["qualified_name"]
    }
