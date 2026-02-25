# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Build structural graph records for ingestion."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Dict, Iterable, Optional, Tuple

from typing import Protocol
from ...runtime import identity as ids
from ...runtime.text import canonical_span_bytes
from ..analysis.graph import module_id_for
from ..config import CALLABLE_NODE_TYPES
from ..contracts import select_strict_call_candidate
from ..tools.call_extraction import normalize_call_identifiers
from .normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileSnapshot,
    SemanticNodeRecord,
)


class CoreStore(Protocol):
    def insert_structural_node(self, conn, **kwargs) -> None: ...
    def insert_node_instance(self, conn, **kwargs) -> None: ...
    def insert_edge(self, conn, **kwargs) -> None: ...


class StructuralAssembler:
    def __init__(self, conn, store: CoreStore) -> None:
        self.conn = conn
        self.structural_cache: Dict[Tuple[str, str, str], str] = {}
        self._store = store

    def prime_structural_cache(self, snapshot_id: Optional[str]) -> None:
        self.structural_cache = {}
        if not snapshot_id:
            return
        rows = self.conn.execute(
            """
            SELECT sn.structural_id, sn.node_type, sn.language, ni.qualified_name
            FROM structural_nodes sn
            JOIN node_instances ni ON ni.structural_id = sn.structural_id
            WHERE ni.snapshot_id = ?
            """,
            (snapshot_id,),
        ).fetchall()
        for row in rows:
            key = (row["language"], row["node_type"], row["qualified_name"])
            self.structural_cache[key] = row["structural_id"]

    def persist_analysis(
        self,
        snapshot_id: str,
        analysis: AnalysisResult,
        file_snapshot: FileSnapshot,
    ) -> tuple[int, Dict[str, Tuple[str, str]]]:
        analysis = self._normalize_call_records(analysis, file_snapshot)
        nodes = sorted(
            analysis.nodes, key=lambda node: (node.node_type, node.qualified_name)
        )
        edges = sorted(
            analysis.edges,
            key=lambda edge: (
                edge.src_qualified_name,
                edge.dst_qualified_name,
                edge.edge_type,
            ),
        )
        node_count = 0
        node_id_map: Dict[str, Tuple[str, str]] = {}
        for node in nodes:
            structural_id = self._emit_structural_node(node, snapshot_id)
            node_id_map[node.qualified_name] = (structural_id, node.node_type)
            node_count += 1
        self._emit_node_instances(
            snapshot_id, nodes, file_snapshot, node_id_map
        )
        self._emit_edges(snapshot_id, edges, node_id_map)
        return node_count, node_id_map

    def _normalize_call_records(
        self,
        analysis: AnalysisResult,
        file_snapshot: FileSnapshot,
    ) -> AnalysisResult:
        if not analysis.call_records:
            return analysis
        node_language_by_qname = {
            node.qualified_name: node.language for node in analysis.nodes
        }
        resolved_calls = [
            (
                node_language_by_qname.get(
                    record.qualified_name, file_snapshot.record.language
                ),
                record.qualified_name,
                record.node_type,
                list(record.callee_identifiers),
            )
            for record in analysis.call_records
        ]
        normalized = normalize_call_identifiers(resolved_calls)
        module_names = {
            node.qualified_name for node in analysis.nodes if node.node_type == "module"
        }
        symbol_index = _build_symbol_index(analysis.nodes)
        module_lookup = _build_module_lookup(analysis.nodes, module_names)
        import_targets = _build_import_targets(analysis.edges)
        strict_normalized: list[tuple[str, str, str, list[str]]] = []
        for language, qualified, node_type, identifiers in normalized:
            caller_module = module_id_for(qualified, module_names)
            accepted: list[str] = []
            for identifier in identifiers:
                direct_candidates: list[str]
                if "." in identifier:
                    direct_candidates = [identifier]
                else:
                    direct_candidates = list(symbol_index.get(identifier, ()))
                fallback_candidates: list[str] = []
                if not direct_candidates and "." in identifier:
                    fallback_candidates = list(
                        symbol_index.get(identifier.rsplit(".", 1)[-1], ())
                    )
                decision = select_strict_call_candidate(
                    identifier=identifier,
                    direct_candidates=direct_candidates,
                    fallback_candidates=fallback_candidates,
                    caller_module=caller_module,
                    module_lookup=module_lookup,
                    import_targets=import_targets,
                )
                if decision.accepted_candidate:
                    accepted.append(decision.accepted_candidate)
            if accepted:
                strict_normalized.append(
                    (language, qualified, node_type, list(dict.fromkeys(accepted)))
                )
        analysis.call_records = [
            CallRecord(
                qualified_name=qualified,
                node_type=node_type,
                callee_identifiers=callee_identifiers,
            )
            for _language, qualified, node_type, callee_identifiers in strict_normalized
        ]
        return analysis

    def register_module_node(
        self,
        snapshot_id: str,
        file_snapshot: FileSnapshot,
        module_name: str,
        node_type: str = "module",
        metadata: Optional[Dict[str, object]] = None,
    ) -> int:
        if not module_name:
            return 0
        module_node = SemanticNodeRecord(
            language=file_snapshot.record.language,
            node_type=node_type,
            qualified_name=module_name,
            display_name=module_name.split(".")[-1] or module_name,
            file_path=file_snapshot.record.relative_path,
            start_line=1,
            end_line=max(1, file_snapshot.line_count),
            start_byte=0,
            end_byte=file_snapshot.size,
            metadata=metadata,
        )
        structural_id = self._emit_structural_node(module_node, snapshot_id)
        node_map = {module_node.qualified_name: (structural_id, module_node.node_type)}
        self._emit_node_instances(snapshot_id, [module_node], file_snapshot, node_map)
        return 1

    def _emit_structural_node(self, node: SemanticNodeRecord, snapshot_id: str) -> str:
        key = (node.language, node.node_type, node.qualified_name)
        if key in self.structural_cache:
            return self.structural_cache[key]
        structural_id = ids.structural_id(
            node.node_type, node.language, node.qualified_name
        )
        existing = self.conn.execute(
            "SELECT structural_id FROM structural_nodes WHERE structural_id = ?",
            (structural_id,),
        ).fetchone()
        if existing:
            self.structural_cache[key] = existing["structural_id"]
            return existing["structural_id"]
        self._store.insert_structural_node(
            self.conn,
            structural_id=structural_id,
            node_type=node.node_type,
            language=node.language,
            created_snapshot_id=snapshot_id,
        )
        self.structural_cache[key] = structural_id
        return structural_id

    def _emit_node_instances(
        self,
        snapshot_id: str,
        nodes: Iterable[SemanticNodeRecord],
        file_snapshot: FileSnapshot,
        node_id_map: Dict[str, Tuple[str, str]],
    ) -> None:
        for node in nodes:
            structural_id = node_id_map[node.qualified_name][0]
            content_hash = self._node_content_hash(node, file_snapshot)
            self._store.insert_node_instance(
                self.conn,
                instance_id=ids.instance_id(snapshot_id, structural_id),
                structural_id=structural_id,
                snapshot_id=snapshot_id,
                qualified_name=node.qualified_name,
                file_path=node.file_path.as_posix(),
                start_line=node.start_line,
                end_line=node.end_line,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                content_hash=content_hash,
            )

    def _emit_edges(
        self,
        snapshot_id: str,
        edges: Iterable[EdgeRecord],
        node_id_map: Dict[str, Tuple[str, str]],
    ) -> None:
        for edge in edges:
            src_id = self._lookup_structural_id(
                edge.src_language,
                edge.src_node_type,
                edge.src_qualified_name,
                node_id_map,
            )
            dst_id = self._lookup_structural_id(
                edge.dst_language,
                edge.dst_node_type,
                edge.dst_qualified_name,
                node_id_map,
            )
            if not src_id or not dst_id:
                continue
            self._store.insert_edge(
                self.conn,
                snapshot_id=snapshot_id,
                src_structural_id=src_id,
                dst_structural_id=dst_id,
                edge_type=edge.edge_type,
            )

    def _lookup_structural_id(
        self,
        language: str,
        node_type: str,
        qualified_name: str,
        local_map: Dict[str, Tuple[str, str]],
    ) -> Optional[str]:
        local = local_map.get(qualified_name)
        if local and local[1] == node_type:
            return local[0]
        cache_key = (language, node_type, qualified_name)
        return self.structural_cache.get(cache_key)

    def _node_content_hash(
        self, node: SemanticNodeRecord, file_snapshot: FileSnapshot
    ) -> str:
        content = file_snapshot.content
        if (
            node.start_byte is not None
            and node.end_byte is not None
            and 0 <= node.start_byte <= node.end_byte
            and node.end_byte <= len(content)
        ):
            segment = content[node.start_byte : node.end_byte]
            if segment:
                canonical = canonical_span_bytes(segment)
                if canonical:
                    return hashlib.sha1(canonical).hexdigest()
        return file_snapshot.blob_sha


def _build_symbol_index(
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


def _build_module_lookup(
    nodes: Iterable[SemanticNodeRecord],
    module_names: set[str],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for node in nodes:
        if node.node_type not in CALLABLE_NODE_TYPES:
            continue
        lookup[node.qualified_name] = module_id_for(node.qualified_name, module_names)
    return lookup


def _build_import_targets(
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
