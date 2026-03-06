# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dependency edge reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta
from .dependency_edges_fetch import _fetch_dependency_edges
from .dependency_edges_normalize import (
    _normalize_direction,
    _normalize_edge_type,
    _normalize_limit,
)
from .dependency_edges_resolve import (
    _node_lookup,
    _resolve_module_ids,
    _resolve_module_query,
)

REDUCER_META = ReducerMeta(
    reducer_id="dependency_edges",
    category="core",
    scope="codebase",
    investigation_roles=("relations",),
    risk_tier="normal",
    investigation_stage="relationship_analysis",
    placeholders=("DEPENDENCY_EDGES",),
    determinism="strict",
    payload_size_stats=None,
    summary="Explicit module import dependencies. " \
    "Use for analysing module coupling or dependency graphs. " \
    "direction='in' or 'out' scopes module_id filters. " \
    "Scope: module-level import edges. Payload kind: summary.",
    lossy=True,
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
            }
        )
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
        "edge_count": len(enriched),
        "edges": enriched,
    }
    return render_json_payload(body)
