"""Import reference reducer (who imports a module)."""

from __future__ import annotations

from typing import Dict, List

from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="import_references",
    scope="codebase",
    placeholders=("IMPORT_REFERENCES",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="dependency",
    summary="Modules that import the target module(s).",
    lossy=True,
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    query: str | None = None,
    edge_type: str | None = None,
    limit: int | str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="import_references reducer"
    )
    if not module_id and not query:
        raise ValueError("import_references requires module_id or query.")
    target_ids = _resolve_module_ids(conn, snapshot_id, module_id, query)
    edge_type_value = _normalize_edge_type(edge_type)
    limit_value = _normalize_limit(limit)
    edges = _fetch_importers(
        conn, snapshot_id, target_ids, edge_type_value, limit_value
    )
    lookup = _node_lookup(
        conn,
        snapshot_id,
        {edge["from_module_structural_id"] for edge in edges}
        | {edge["to_module_structural_id"] for edge in edges}
        | set(target_ids),
    )
    targets = [
        {
            "module_structural_id": module_id,
            "module_qualified_name": lookup.get(module_id, {}).get("qualified_name"),
            "file_path": lookup.get(module_id, {}).get("file_path"),
        }
        for module_id in target_ids
    ]
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
            }
        )
    body = {
        "module_filter": module_id,
        "query": query,
        "edge_type": edge_type_value or "any",
        "limit": limit_value,
        "target_count": len(targets),
        "targets": targets,
        "edge_source": "sci",
        "edge_count": len(enriched),
        "edges": enriched,
    }
    return render_json_payload(body)


def _resolve_module_ids(
    conn,
    snapshot_id: str,
    module_name: str | None,
    query: str | None,
) -> List[str]:
    if module_name:
        normalized = str(module_name).strip()
        if not normalized:
            raise ValueError("import_references module_id must be non-empty.")
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
            (snapshot_id, normalized, f"{normalized}.%", normalized),
        ).fetchall()
        module_ids = [row["structural_id"] for row in rows]
        if not module_ids:
            raise ValueError(
                f"Module '{normalized}' not found in snapshot '{snapshot_id}'."
            )
        return module_ids
    normalized = str(query).strip() if query else ""
    if not normalized:
        raise ValueError("import_references query must be non-empty.")
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


def _normalize_edge_type(edge_type: str | None) -> str | None:
    if edge_type is None:
        return "IMPORTS_DECLARED"
    normalized = str(edge_type).strip()
    if not normalized:
        return "IMPORTS_DECLARED"
    if normalized.lower() in {"any", "*"}:
        return None
    return normalized


def _normalize_limit(limit: int | str | None) -> int | None:
    if limit is None:
        return None
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("import_references limit must be an integer.")
    if value <= 0:
        raise ValueError("import_references limit must be positive.")
    return min(value, 10000)


def _fetch_importers(
    conn,
    snapshot_id: str,
    target_ids: List[str],
    edge_type: str | None,
    limit: int | None,
) -> List[Dict[str, str]]:
    if not target_ids:
        return []
    clauses = [
        "e.snapshot_id = ?",
        "sn_src.node_type = 'module'",
        "sn_dst.node_type = 'module'",
    ]
    params: list[object] = [snapshot_id]
    if edge_type:
        clauses.append("e.edge_type = ?")
        params.append(edge_type)
    placeholders = ",".join("?" for _ in target_ids)
    clauses.append(f"e.dst_structural_id IN ({placeholders})")
    params.extend(target_ids)
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
