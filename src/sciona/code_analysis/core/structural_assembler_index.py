# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Index helpers used by StructuralAssembler."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from ..analysis.graph import module_id_for
from ..config import CALLABLE_NODE_TYPES
from .normalize.model import EdgeRecord, SemanticNodeRecord


def build_symbol_index(
    nodes: Iterable[SemanticNodeRecord],
) -> dict[str, list[str]]:
    index_sets: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        if node.node_type not in CALLABLE_NODE_TYPES:
            continue
        qname = node.qualified_name
        index_sets[qname].add(qname)
        terminal = qname.rsplit(".", 1)[-1]
        if terminal:
            index_sets[terminal].add(qname)
    return {key: sorted(values) for key, values in index_sets.items()}


def build_module_lookup(
    nodes: Iterable[SemanticNodeRecord],
    module_names: set[str],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for node in nodes:
        if node.node_type not in CALLABLE_NODE_TYPES:
            continue
        lookup[node.qualified_name] = module_id_for(node.qualified_name, module_names)
    return lookup


def build_import_targets(
    edges: Iterable[EdgeRecord],
) -> dict[str, set[str]]:
    targets: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if (
            edge.edge_type != "IMPORTS_DECLARED"
            or edge.src_node_type != "module"
            or edge.dst_node_type != "module"
        ):
            continue
        targets[edge.src_qualified_name].add(edge.dst_qualified_name)
    return targets


__all__ = ["build_import_targets", "build_module_lookup", "build_symbol_index"]
