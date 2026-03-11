# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dependency edge reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..runtime.edge_types import MODULE_DEPENDENCY_EDGE_TYPES
from .helpers.shared.connection import require_connection
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="dependency_edges",
    category="coupling",
    placeholder="DEPENDENCY_EDGES",
    summary="Explicit module import dependencies. "
    "Use for analysing module coupling or dependency graphs. "
    "direction='in' or 'out' scopes module_id filters. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    from_module_id: str | None = None,
    to_module_id: str | None = None,
    query: str | None = None,
    edge_type: str | None = None,
    direction: str | None = None,
    limit: int | str | None = None,
    compact: bool | None = None,
    top_k: int | str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="dependency_edges reducer"
    )
    dir_value = _normalize_direction(direction)
    source_selector = from_module_id
    from_ids: Optional[List[str]] = None
    to_ids: Optional[List[str]] = None
    module_ids: Optional[List[str]] = None
    if module_id and not from_module_id and not to_module_id:
        module_ids = _resolve_module_ids(conn, snapshot_id, module_id)
        if dir_value == "out":
            from_ids = module_ids
        elif dir_value == "in":
            to_ids = module_ids
    else:
        if source_selector:
            from_ids = _resolve_module_ids(conn, snapshot_id, source_selector)
        if module_id and not from_module_id:
            from_ids = _resolve_module_ids(conn, snapshot_id, module_id)
        if to_module_id:
            to_ids = _resolve_module_ids(conn, snapshot_id, to_module_id)
    if query:
        query_ids = _resolve_module_query(conn, snapshot_id, query)
        if from_ids is None and to_ids is None and module_ids is None:
            from_ids = query_ids
        else:
            if from_ids is not None:
                from_ids = [value for value in from_ids if value in query_ids]
            if to_ids is not None:
                to_ids = [value for value in to_ids if value in query_ids]
            if module_ids is not None:
                module_ids = [value for value in module_ids if value in query_ids]
    edge_type_value = _normalize_edge_type(edge_type)
    limit_value = _normalize_limit(limit)
    compact_mode = bool(compact)
    top_k_value = _normalize_top_k(top_k)
    if from_ids == [] or to_ids == [] or module_ids == []:
        edges = []
    else:
        edges = _fetch_dependency_edges(
            conn,
            snapshot_id,
            from_ids=from_ids,
            to_ids=to_ids,
            edge_type=edge_type_value,
            limit=limit_value,
            direction=dir_value,
            module_ids=module_ids,
        )
    lookup = _node_lookup(
        conn,
        snapshot_id,
        {edge["from_module_structural_id"] for edge in edges}
        | {edge["to_module_structural_id"] for edge in edges},
    )
    enriched = []
    for edge in edges:
        src = lookup.get(edge["from_module_structural_id"], {})
        dst = lookup.get(edge["to_module_structural_id"], {})
        enriched.append(
            {
                "from_module_structural_id": edge["from_module_structural_id"],
                "to_module_structural_id": edge["to_module_structural_id"],
                "from_module_qualified_name": src.get("qualified_name"),
                "to_module_qualified_name": dst.get("qualified_name"),
                "from_file_path": src.get("file_path"),
                "to_file_path": dst.get("file_path"),
                "edge_type": edge["edge_type"],
                "edge_source": "sci",
                "row_origin": "committed",
            }
        )
    committed_count = len(enriched)
    body = {
        "payload_kind": "summary",
        "module_filter": module_id,
        "from_module_filter": from_module_id,
        "to_module_filter": to_module_id,
        "query": query,
        "edge_type": edge_type_value or "any",
        "direction": dir_value,
        "limit": limit_value,
        "edge_source": "sci",
        "edge_count": committed_count,
        "listed_edge_count": committed_count,
        "committed_count": committed_count,
        "overlay_added_count": 0,
        "overlay_removed_count": 0,
        "edges": enriched,
    }
    if compact_mode:
        body = _compact_payload(
            body,
            module_filter=module_id,
            direction=dir_value,
            top_k=top_k_value,
        )
    return render_json_payload(body)


def _fetch_edges(
    conn,
    snapshot_id: str,
    from_ids: Optional[List[str]],
    to_ids: Optional[List[str]],
    edge_type: str | None,
    limit: int | None,
) -> List[Dict[str, str]]:
    clauses = [
        "e.snapshot_id = ?",
        "sn_src.node_type = 'module'",
        "sn_dst.node_type = 'module'",
    ]
    params: list[object] = [snapshot_id]
    if edge_type:
        clauses.append("e.edge_type = ?")
        params.append(edge_type)
    if from_ids:
        placeholders = ",".join("?" for _ in from_ids)
        clauses.append(f"e.src_structural_id IN ({placeholders})")
        params.extend(from_ids)
    if to_ids:
        placeholders = ",".join("?" for _ in to_ids)
        clauses.append(f"e.dst_structural_id IN ({placeholders})")
        params.extend(to_ids)
    where = " AND ".join(clauses)
    limit_clause = " LIMIT ?" if limit else ""
    if limit:
        params.append(limit)
    rows = conn.execute(
        f"""
        SELECT e.src_structural_id, e.dst_structural_id, e.edge_type
        FROM edges e
        JOIN structural_nodes sn_src ON sn_src.structural_id = e.src_structural_id
        JOIN structural_nodes sn_dst ON sn_dst.structural_id = e.dst_structural_id
        WHERE {where}
        ORDER BY e.src_structural_id, e.dst_structural_id
        {limit_clause}
        """,
        params,
    ).fetchall()
    return [
        {
            "from_module_structural_id": row["src_structural_id"],
            "to_module_structural_id": row["dst_structural_id"],
            "edge_type": row["edge_type"],
        }
        for row in rows
    ]


def _fetch_dependency_edges(
    conn,
    snapshot_id: str,
    *,
    from_ids: Optional[List[str]],
    to_ids: Optional[List[str]],
    edge_type: str | None,
    limit: int | None,
    direction: str,
    module_ids: Optional[List[str]],
) -> List[Dict[str, str]]:
    if module_ids and direction == "both" and from_ids is None and to_ids is None:
        outgoing = _fetch_edges(conn, snapshot_id, module_ids, None, edge_type, limit)
        incoming = _fetch_edges(conn, snapshot_id, None, module_ids, edge_type, limit)
        merged: dict[tuple[str, str, str], Dict[str, str]] = {}
        for entry in outgoing + incoming:
            key = (
                entry.get("from_module_structural_id"),
                entry.get("to_module_structural_id"),
                entry.get("edge_type"),
            )
            merged[key] = entry
        return sorted(
            merged.values(),
            key=lambda item: (
                item.get("from_module_structural_id"),
                item.get("to_module_structural_id"),
                item.get("edge_type"),
            ),
        )
    return _fetch_edges(conn, snapshot_id, from_ids, to_ids, edge_type, limit)


def _normalize_edge_type(edge_type: str | None) -> str | None:
    if edge_type is None:
        return "IMPORTS_DECLARED"
    normalized = str(edge_type).strip()
    if not normalized:
        return "IMPORTS_DECLARED"
    if normalized.lower() in {"any", "*"}:
        return None
    if normalized not in MODULE_DEPENDENCY_EDGE_TYPES:
        allowed = ", ".join(sorted(MODULE_DEPENDENCY_EDGE_TYPES))
        raise ValueError(
            f"dependency_edges edge_type must be one of: {allowed}, any, *."
        )
    return normalized


def _normalize_direction(direction: str | None) -> str:
    if not direction:
        return "both"
    value = str(direction).strip().lower()
    if value in {"in", "out", "both"}:
        return value
    raise ValueError("dependency_edges direction must be one of: in, out, both.")


def _normalize_limit(limit: int | str | None) -> int | None:
    if limit is None:
        return None
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("dependency_edges limit must be an integer.")
    if value <= 0:
        raise ValueError("dependency_edges limit must be positive.")
    return min(value, 10000)


def _normalize_top_k(top_k: int | str | None) -> int:
    if top_k is None:
        return 5
    try:
        value = int(top_k)
    except (TypeError, ValueError) as exc:
        raise ValueError("dependency_edges top_k must be an integer.") from exc
    if value <= 0:
        raise ValueError("dependency_edges top_k must be positive.")
    return min(value, 50)


def _compact_payload(
    body: Dict[str, object],
    *,
    module_filter: str | None,
    direction: str,
    top_k: int,
) -> Dict[str, object]:
    edges = list(body.get("edges", []))
    payload: Dict[str, object] = {
        "payload_kind": "compact_summary",
        "module_filter": module_filter,
        "from_module_filter": body.get("from_module_filter"),
        "to_module_filter": body.get("to_module_filter"),
        "query": body.get("query"),
        "edge_type": body.get("edge_type"),
        "direction": direction,
        "edge_source": body.get("edge_source"),
        "edge_count": body.get("edge_count"),
        "committed_count": body.get("committed_count"),
        "overlay_added_count": body.get("overlay_added_count"),
        "overlay_removed_count": body.get("overlay_removed_count"),
        "top_k": top_k,
    }
    if module_filter and direction in {"in", "out", "both"}:
        payload["counterpart_modules"] = _group_counterparts(
            edges,
            direction=direction,
            top_k=top_k,
        )
    else:
        payload["edges_preview"] = {
            "count": len(edges),
            "truncated": len(edges) > top_k,
            "entries": edges[:top_k],
        }
    return payload


def _group_counterparts(
    edges: List[Dict[str, str]],
    *,
    direction: str,
    top_k: int,
) -> Dict[str, object]:
    grouped: dict[str, Dict[str, object]] = {}
    for edge in edges:
        if direction == "in":
            structural_id = edge["from_module_structural_id"]
            qualified_name = edge["from_module_qualified_name"]
            file_path = edge["from_file_path"]
            incoming = 1
            outgoing = 0
        elif direction == "out":
            structural_id = edge["to_module_structural_id"]
            qualified_name = edge["to_module_qualified_name"]
            file_path = edge["to_file_path"]
            incoming = 0
            outgoing = 1
        else:
            src_key = edge["from_module_structural_id"]
            dst_key = edge["to_module_structural_id"]
            for structural_id, qualified_name, file_path, incoming, outgoing in (
                (
                    src_key,
                    edge["from_module_qualified_name"],
                    edge["from_file_path"],
                    1,
                    0,
                ),
                (
                    dst_key,
                    edge["to_module_qualified_name"],
                    edge["to_file_path"],
                    0,
                    1,
                ),
            ):
                entry = grouped.setdefault(
                    structural_id,
                    {
                        "module_structural_id": structural_id,
                        "module_qualified_name": qualified_name,
                        "file_path": file_path,
                        "incoming_edge_count": 0,
                        "outgoing_edge_count": 0,
                        "edge_count": 0,
                    },
                )
                entry["incoming_edge_count"] += incoming
                entry["outgoing_edge_count"] += outgoing
                entry["edge_count"] += incoming + outgoing
            continue
        entry = grouped.setdefault(
            structural_id,
            {
                "module_structural_id": structural_id,
                "module_qualified_name": qualified_name,
                "file_path": file_path,
                "incoming_edge_count": 0,
                "outgoing_edge_count": 0,
                "edge_count": 0,
            },
        )
        entry["incoming_edge_count"] += incoming
        entry["outgoing_edge_count"] += outgoing
        entry["edge_count"] += incoming + outgoing
    entries = sorted(
        grouped.values(),
        key=lambda entry: (-int(entry["edge_count"]), str(entry["module_qualified_name"])),
    )
    return {
        "count": len(entries),
        "truncated": len(entries) > top_k,
        "entries": entries[:top_k],
    }


def _resolve_module_ids(conn, snapshot_id: str, module_name: str) -> List[str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (ni.qualified_name = ? OR ni.qualified_name LIKE ? OR sn.structural_id = ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, module_name, f"{module_name}.%", module_name),
    ).fetchall()
    module_ids = [row["structural_id"] for row in rows]
    if not module_ids:
        raise ValueError(
            f"Module '{module_name}' not found in snapshot '{snapshot_id}'."
        )
    return module_ids


def _resolve_module_query(conn, snapshot_id: str, query: str) -> List[str]:
    normalized = str(query).strip()
    if not normalized:
        raise ValueError("dependency_edges query must be non-empty.")
    lowered = normalized.lower()
    rows = conn.execute(
        """
        SELECT sn.structural_id
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type = 'module'
          AND (sn.structural_id = ? OR LOWER(ni.qualified_name) LIKE ?)
        ORDER BY ni.qualified_name
        """,
        (snapshot_id, normalized, f"%{lowered}%"),
    ).fetchall()
    module_ids = [row["structural_id"] for row in rows]
    if not module_ids:
        raise ValueError(
            f"No modules match query '{normalized}' in snapshot '{snapshot_id}'."
        )
    return module_ids


def _node_lookup(
    conn, snapshot_id: str, node_ids: set[str]
) -> Dict[str, Dict[str, str]]:
    if not node_ids:
        return {}
    placeholders = ",".join("?" for _ in node_ids)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, ni.qualified_name, ni.file_path
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
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    }


__all__ = [
    "REDUCER_META",
    "render",
    "_normalize_direction",
    "_normalize_edge_type",
    "_normalize_limit",
    "_normalize_top_k",
    "_node_lookup",
    "_resolve_module_ids",
    "_resolve_module_query",
    "_fetch_dependency_edges",
    "_fetch_edges",
]
