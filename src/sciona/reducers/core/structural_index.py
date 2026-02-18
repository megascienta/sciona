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

from ..metadata import ReducerMeta
from ..helpers import queries
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ...code_analysis.analysis.orderings import order_edges, order_nodes
from ..helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ..helpers.types import StructuralIndexPayload

REDUCER_META = ReducerMeta(
    reducer_id="structural_index",
    category="core",
    scope="codebase",
    placeholders=("STRUCTURAL_INDEX",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Canonical structural index of the codebase. " \
    "Use for global structural reasoning or validation. " \
    "Scope: entire SCI snapshot.",
)


def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    conn = require_connection(conn)
    payload = run(snapshot_id, conn=conn, repo_root=repo_root)
    return render_json_payload(payload)


CLASS_NODE_TYPES = {"class", "interface"}
CALLABLE_NODE_TYPES = {"function", "method"}
FUNCTION_NODE_TYPES = {"function"}
METHOD_NODE_TYPES = {"method"}


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
        class_counts,
        file_path_votes,
        function_languages,
        method_languages,
    ) = _module_summaries(
        conn,
        snapshot_id,
        module_graph,
    )
    file_entries = _file_entries(conn, snapshot_id, file_assignments, file_path_votes)
    class_entries = _class_entries(conn, snapshot_id, module_graph.structural_lookup)
    function_stats = _callable_stats(function_counts, function_languages)
    method_stats = _callable_stats(method_counts, method_languages)
    import_edges = _import_edges(module_graph)
    import_cycles = _import_cycles(import_edges)

    return {
        "projection": "structural_index",
        "projection_version": "1.0",
        "modules": {
            "count": len(module_entries),
            "entries": module_entries,
        },
        "files": {
            "count": len(file_entries),
            "entries": file_entries,
        },
        "classes": {
            "count": len(class_entries),
            "entries": class_entries,
            "by_module": _count_to_entries(
                class_counts, key_name="module_qualified_name"
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


def _module_summaries(
    conn, snapshot_id: str, module_graph
) -> Tuple[
    List[Dict[str, object]],
    Dict[str, str],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, Counter[str]],
    Counter[str],
    Counter[str],
]:
    module_files: Dict[str, set[str]] = {module: set() for module in module_graph.nodes}
    function_counts: Dict[str, int] = {module: 0 for module in module_graph.nodes}
    method_counts: Dict[str, int] = {module: 0 for module in module_graph.nodes}
    class_counts: Dict[str, int] = {module: 0 for module in module_graph.nodes}
    function_languages: Counter[str] = Counter()
    method_languages: Counter[str] = Counter()
    file_assignments: Dict[str, str] = {}
    file_path_votes: Dict[str, Counter[str]] = defaultdict(Counter)
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    for row in rows:
        structural_id = row["structural_id"]
        module_name = module_graph.structural_lookup.get(structural_id)
        if not module_name:
            continue
        node_type = row["node_type"]
        file_path = row["file_path"]
        if file_path and node_type != "directory":
            module_files.setdefault(module_name, set()).add(file_path)
            file_path_votes[file_path][module_name] += 1
        if node_type in FUNCTION_NODE_TYPES:
            function_counts[module_name] = function_counts.get(module_name, 0) + 1
            function_languages[row["language"]] += 1
        if node_type in METHOD_NODE_TYPES:
            method_counts[module_name] = method_counts.get(module_name, 0) + 1
            method_languages[row["language"]] += 1
        if node_type in CLASS_NODE_TYPES:
            class_counts[module_name] = class_counts.get(module_name, 0) + 1
    module_entries: List[Dict[str, object]] = []
    for module in sorted(module_graph.nodes):
        files = module_files.get(module, set())
        module_entries.append(
            {
                "module_qualified_name": module,
                "language": module_graph.languages.get(module, ""),
                "file_count": len(files),
                "class_count": class_counts.get(module, 0),
                "function_count": function_counts.get(module, 0),
                "method_count": method_counts.get(module, 0),
            }
        )
        for file_path in files:
            file_assignments[file_path] = module
    order_nodes(module_entries, key="module_qualified_name")
    return (
        module_entries,
        file_assignments,
        function_counts,
        method_counts,
        class_counts,
        file_path_votes,
        function_languages,
        method_languages,
    )


def _file_entries(
    conn,
    snapshot_id: str,
    module_assignments: Dict[str, str],
    votes: Dict[str, Counter[str]],
) -> List[Dict[str, object]]:
    rows = conn.execute(
        """
        SELECT DISTINCT ni.file_path AS path
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type != 'directory'
        """,
        (snapshot_id,),
    ).fetchall()
    entries: List[Dict[str, object]] = []
    for row in rows:
        path = row["path"]
        module_name = module_assignments.get(path)
        if not module_name and path in votes:
            module_name = votes[path].most_common(1)[0][0]
        entries.append(
            {
                "path": path,
                "module_qualified_name": module_name,
            }
        )
    order_nodes(entries, key="path")
    return entries


def _class_entries(
    conn, snapshot_id: str, structural_lookup: Dict[str, str]
) -> List[Dict[str, object]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ('class', 'interface')
        """,
        (snapshot_id,),
    ).fetchall()
    entries: List[Dict[str, object]] = []
    for row in rows:
        module_name = structural_lookup.get(row["structural_id"])
        entries.append(
            {
                "structural_id": row["structural_id"],
                "qualified_name": row["qualified_name"],
                "module_qualified_name": module_name,
                "language": row["language"],
                "file_path": row["file_path"],
                "line_span": [row["start_line"], row["end_line"]],
            }
        )
    order_nodes(entries, key="qualified_name")
    return entries


def _callable_stats(
    counts: Dict[str, int], language_counts: Counter[str]
) -> Dict[str, object]:
    total = sum(counts.values())
    per_module = _count_to_entries(counts, key_name="module_qualified_name")
    language_entries = [
        {"language": language or "unknown", "count": count}
        for language, count in language_counts.items()
        if count
    ]
    order_nodes(language_entries, key=lambda item: (-item["count"], item["language"]))
    return {
        "total": total,
        "by_module": per_module,
        "by_language": language_entries,
    }


@dataclass(frozen=True)
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


def _count_to_entries(counts: Dict[str, int], key_name: str) -> List[Dict[str, object]]:
    entries = [
        {key_name: key, "count": value} for key, value in counts.items() if value
    ]
    order_nodes(entries, key=lambda item: (-item["count"], item[key_name]))
    return entries
