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

@dataclass
class _ModuleGraph:
    nodes: Set[str]
    outgoing: Dict[str, Sequence[str]]
    incoming: Dict[str, Sequence[str]]
    languages: Dict[str, str]
    structural_lookup: Dict[str, str]

def _build_module_graph(conn, snapshot_id: str, repo_root: str | Path) -> _ModuleGraph:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    module_languages: Dict[str, str] = {
        row["qualified_name"]: row["language"]
        for row in rows
        if row["node_type"] == "module" and row["qualified_name"]
    }
    structural_lookup = queries.module_id_lookup(conn, snapshot_id)
    module_names: Set[str] = set(module_languages)
    edges = load_artifact_edges(
        Path(repo_root),
        edge_kinds=["IMPORTS_DECLARED"],
    )
    outgoing: Dict[str, Set[str]] = {module: set() for module in module_names}
    incoming: Dict[str, Set[str]] = {module: set() for module in module_names}
    for src_id, dst_id, _ in edges:
        src = structural_lookup.get(src_id)
        dst = structural_lookup.get(dst_id)
        if not src or not dst or src == dst:
            continue
        outgoing.setdefault(src, set()).add(dst)
        incoming.setdefault(dst, set()).add(src)
    nodes = set(module_names) | set(outgoing) | set(incoming)
    return _ModuleGraph(
        nodes=nodes,
        outgoing={node: sorted(neighbors) for node, neighbors in outgoing.items()},
        incoming={node: sorted(neighbors) for node, neighbors in incoming.items()},
        languages=module_languages,
        structural_lookup=structural_lookup,
    )

def _import_edges(module_graph) -> List[Dict[str, str]]:
    edges: List[Dict[str, str]] = []
    for src, neighbors in module_graph.outgoing.items():
        for dst in neighbors:
            edges.append(
                {"from_module_qualified_name": src, "to_module_qualified_name": dst}
            )
    order_edges(
        edges, fields=("from_module_qualified_name", "to_module_qualified_name")
    )
    return edges

def _import_cycles(import_edges: List[Dict[str, str]]) -> List[Dict[str, List[str]]]:
    graph = nx.DiGraph()
    for edge in import_edges:
        graph.add_edge(
            edge["from_module_qualified_name"], edge["to_module_qualified_name"]
        )
    cycles: List[Dict[str, List[str]]] = []
    for component in nx.strongly_connected_components(graph):
        if len(component) <= 1:
            continue
        members = sorted(component)
        cycles.append({"module_qualified_names": members})
    order_nodes(
        cycles, key=lambda entry: tuple(entry.get("module_qualified_names", ()))
    )
    return cycles
