# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol reference reducer."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ...helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta
from .symbol_references_candidates import (
    _fetch_candidates,
    _rank_candidates,
    _score_identifier,
)
from .symbol_references_normalize import _NODE_TYPES, _normalize_kind, _normalize_limit
from .symbol_references_references import (
    _build_references,
    _call_references,
    _import_references,
    _node_lookup,
)

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
