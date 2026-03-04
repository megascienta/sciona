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

TYPE_NODE_TYPES = {"type"}

CALLABLE_NODE_TYPES = {"callable"}

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
        qualified_name = row["qualified_name"]
        file_path = row["file_path"]
        if file_path:
            module_files.setdefault(module_name, set()).add(file_path)
            file_path_votes[file_path][module_name] += 1
        if node_type in CALLABLE_NODE_TYPES:
            callable_suffix = (
                qualified_name[len(module_name) + 1 :]
                if qualified_name.startswith(f"{module_name}.")
                else qualified_name
            )
            if "." in callable_suffix:
                method_counts[module_name] = method_counts.get(module_name, 0) + 1
                method_languages[row["language"]] += 1
            else:
                function_counts[module_name] = function_counts.get(module_name, 0) + 1
                function_languages[row["language"]] += 1
        if node_type in TYPE_NODE_TYPES:
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
          AND sn.node_type = 'type'
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

def _count_to_entries(counts: Dict[str, int], key_name: str) -> List[Dict[str, object]]:
    entries = [
        {key_name: key, "count": value} for key, value in counts.items() if value
    ]
    order_nodes(entries, key=lambda item: (-item["count"], item[key_name]))
    return entries
