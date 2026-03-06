# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Canonical structural_index reducer.

Cost profile: O(nodes + edges) for the active snapshot because it reads every
node instance and aggregates module/edge metadata exactly once. It must never
diff multiple snapshots.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

import networkx as nx

from ...metadata import ReducerMeta
from ...helpers import queries
from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ....code_analysis.analysis.orderings import order_edges, order_nodes
from ...helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ...helpers.types import StructuralIndexPayload
from .structural_index_entries import (
    _callable_stats,
    _class_entries,
    _count_to_entries,
    _file_entries,
    _module_summaries,
)
from .structural_index_graph import _build_module_graph, _import_cycles, _import_edges

REDUCER_META = ReducerMeta(
    reducer_id="structural_index",
    category="structure",
    risk_tier="normal",
    stage="initial_scan",
    placeholder="STRUCTURAL_INDEX",
    summary="Canonical structural index of the codebase. " \
    "Use for global structural reasoning or validation. ",
)

def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    conn = require_connection(conn)
    payload = run(snapshot_id, conn=conn, repo_root=repo_root)
    return render_json_payload(payload)

def run(snapshot_id: str, **params) -> StructuralIndexPayload:
    conn = params.get("conn")
    if conn is None:
        raise ValueError(
            "structural_index reducer requires an active database connection."
        )
    repo_root = params.get("repo_root")
    if not repo_root:
        raise ValueError(
            "structural_index reducer requires repo_root for artifact graph traversal."
        )
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row or not row["is_committed"]:
        raise ValueError("structural_index reducer requires a committed snapshot.")
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="structural_index reducer"
    )

    artifact_available = artifact_db_available(Path(repo_root))
    if not artifact_available:
        raise ValueError("structural_index reducer requires the artifact database.")
    module_graph = _build_module_graph(conn, snapshot_id, repo_root)
    (
        module_entries,
        file_assignments,
        function_counts,
        method_counts,
        classifier_counts,
        file_path_votes,
        function_languages,
        method_languages,
    ) = _module_summaries(
        conn,
        snapshot_id,
        module_graph,
    )
    file_entries = _file_entries(conn, snapshot_id, file_assignments, file_path_votes)
    classifier_entries = _class_entries(
        conn, snapshot_id, module_graph.structural_lookup
    )
    function_stats = _callable_stats(function_counts, function_languages)
    method_stats = _callable_stats(method_counts, method_languages)
    import_edges = _import_edges(module_graph)
    import_cycles = _import_cycles(import_edges)

    return {
        "projection": "structural_index",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "modules": {
            "count": len(module_entries),
            "entries": module_entries,
        },
        "files": {
            "count": len(file_entries),
            "entries": file_entries,
        },
        "classifiers": {
            "count": len(classifier_entries),
            "entries": classifier_entries,
            "by_module": _count_to_entries(
                classifier_counts, key_name="module_qualified_name"
            ),
        },
        "functions": function_stats,
        "methods": method_stats,
        "imports": {
            "edge_count": len(import_edges),
            "edges": import_edges,
            "artifact_available": artifact_available,
            "edge_source": "artifact_db" if artifact_available else "none",
        },
        "import_cycles": import_cycles,
    }
