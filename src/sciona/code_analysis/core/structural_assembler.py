# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Build structural graph records for ingestion."""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from typing import Protocol
from ...runtime import identity as ids
from ..analysis.graph import module_id_for
from ..contracts import select_strict_call_candidate
from ..tools.call_extraction import normalize_call_identifiers
from .structural_assembler_emit import (
    emit_edges,
    emit_node_instances,
    lookup_structural_id,
)
from .structural_assembler_hash import node_content_hash
from .structural_assembler_index import (
    build_expanded_import_targets,
    build_import_targets,
    build_module_lookup,
    build_symbol_index,
)
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
    def insert_synthetic_node(self, conn, **kwargs) -> None: ...
    def insert_synthetic_node_instance(self, conn, **kwargs) -> None: ...
    def insert_edge(self, conn, **kwargs) -> None: ...


class StructuralAssembler:
    def __init__(self, conn, store: CoreStore) -> None:
        self.conn = conn
        self.structural_cache: Dict[Tuple[str, str, str], str] = {}
        self._store = store
        self.call_gate_diagnostics: dict[str, object] = {
            "identifiers_total": 0,
            "accepted_identifiers": 0,
            "dropped_identifiers": 0,
            "accepted_by_provenance": {},
            "dropped_by_reason": {},
            "dropped_by_resolver": 0,
            "resolver_accepted_assembler_dropped": 0,
        }

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
        self._validate_lexical_containment(analysis)
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

    def _validate_lexical_containment(self, analysis: AnalysisResult) -> None:
        structural_nodes = {
            (node.node_type, node.qualified_name): node
            for node in analysis.nodes
            if node.node_type in {"module", "type", "callable"}
        }
        parent_by_child: dict[tuple[str, str], tuple[str, str]] = {}
        for edge in analysis.edges:
            if edge.edge_type != "LEXICALLY_CONTAINS":
                continue
            parent_key = (edge.src_node_type, edge.src_qualified_name)
            child_key = (edge.dst_node_type, edge.dst_qualified_name)
            if child_key[0] == "module":
                raise ValueError("Lexical containment cannot target a module node.")
            existing_parent = parent_by_child.get(child_key)
            if existing_parent and existing_parent != parent_key:
                raise ValueError(
                    "Structural node has multiple lexical parents: "
                    f"{child_key[1]} <- {existing_parent[1]}, {parent_key[1]}"
                )
            parent_by_child[child_key] = parent_key
            parent_node = structural_nodes.get(parent_key)
            child_node = structural_nodes.get(child_key)
            if not parent_node or not child_node:
                continue
            if (
                parent_node.start_byte is None
                or parent_node.end_byte is None
                or child_node.start_byte is None
                or child_node.end_byte is None
            ):
                continue
            enclosed = (
                parent_node.start_byte <= child_node.start_byte
                and parent_node.end_byte >= child_node.end_byte
            )
            identical_span = (
                parent_node.start_byte == child_node.start_byte
                and parent_node.end_byte == child_node.end_byte
            )
            if not enclosed or identical_span:
                raise ValueError(
                    "Lexical containment span invariant violated: "
                    f"{parent_node.qualified_name} does not enclose {child_node.qualified_name}"
                )
        for key in structural_nodes:
            node_type, qualified_name = key
            if node_type == "module":
                continue
            if key not in parent_by_child:
                raise ValueError(
                    "Structural node missing lexical parent: "
                    f"{qualified_name} ({node_type})"
                )
        for child_key in parent_by_child:
            seen: set[tuple[str, str]] = set()
            current = child_key
            while current in parent_by_child:
                if current in seen:
                    raise ValueError(
                        "Lexical containment cycle detected involving "
                        f"{current[1]}"
                    )
                seen.add(current)
                current = parent_by_child[current]

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
        symbol_index = build_symbol_index(analysis.nodes)
        module_lookup = build_module_lookup(analysis.nodes, module_names)
        import_targets = build_import_targets(analysis.edges)
        expanded_import_targets = build_expanded_import_targets(analysis.edges)
        strict_normalized: list[tuple[str, str, str, list[str]]] = []
        local_totals: dict[str, object] = {
            "identifiers_total": 0,
            "accepted_identifiers": 0,
            "dropped_identifiers": 0,
            "accepted_by_provenance": {},
            "dropped_by_reason": {},
            "dropped_by_resolver": 0,
            "resolver_accepted_assembler_dropped": 0,
        }
        for language, qualified, node_type, identifiers in normalized:
            caller_module = module_id_for(qualified, module_names)
            caller_ancestors = (
                _module_qname_ancestors(caller_module) if caller_module else set()
            )
            accepted: list[str] = []
            for identifier in identifiers:
                local_totals["identifiers_total"] = (
                    int(local_totals["identifiers_total"]) + 1
                )
                direct_candidates: list[str]
                if "." in identifier:
                    direct_candidates = list(symbol_index.get(identifier, ()))
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
                    expanded_import_targets=expanded_import_targets,
                    caller_ancestor_modules=caller_ancestors,
                )
                if decision.accepted_candidate:
                    accepted.append(decision.accepted_candidate)
                    local_totals["accepted_identifiers"] = (
                        int(local_totals["accepted_identifiers"]) + 1
                    )
                    self._inc_counter_map(
                        local_totals, "accepted_by_provenance", decision.accepted_provenance
                    )
                else:
                    local_totals["dropped_identifiers"] = (
                        int(local_totals["dropped_identifiers"]) + 1
                    )
                    local_totals["dropped_by_resolver"] = (
                        int(local_totals["dropped_by_resolver"]) + 1
                    )
                    self._inc_counter_map(
                        local_totals, "dropped_by_reason", decision.dropped_reason
                    )
            if accepted:
                strict_normalized.append(
                    (language, qualified, node_type, list(dict.fromkeys(accepted)))
                )
        self._merge_call_gate_diagnostics(local_totals)
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

    def register_synthetic_module_node(
        self,
        snapshot_id: str,
        file_snapshot: FileSnapshot,
        module_name: str,
        node_type: str = "entry_point",
    ) -> int:
        if not module_name:
            return 0
        synthetic_id = ids.structural_id(node_type, "synthetic", module_name)
        self._store.insert_synthetic_node(
            self.conn,
            synthetic_id=synthetic_id,
            node_type=node_type,
            created_snapshot_id=snapshot_id,
        )
        self._store.insert_synthetic_node_instance(
            self.conn,
            instance_id=ids.instance_id(snapshot_id, synthetic_id),
            synthetic_id=synthetic_id,
            snapshot_id=snapshot_id,
            qualified_name=module_name,
            file_path=file_snapshot.record.relative_path.as_posix(),
            start_line=1,
            end_line=max(1, file_snapshot.line_count),
            start_byte=0,
            end_byte=file_snapshot.size,
            content_hash=node_content_hash(
                SemanticNodeRecord(
                    language="synthetic",
                    node_type=node_type,
                    qualified_name=module_name,
                    display_name=module_name.split(".")[-1] or module_name,
                    file_path=file_snapshot.record.relative_path,
                    start_line=1,
                    end_line=max(1, file_snapshot.line_count),
                    start_byte=0,
                    end_byte=file_snapshot.size,
                    metadata=None,
                ),
                file_snapshot,
            ),
        )
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
        emit_node_instances(
            self.conn,
            self._store,
            snapshot_id,
            nodes,
            file_snapshot,
            node_id_map,
            self._node_content_hash,
        )

    def _emit_edges(
        self,
        snapshot_id: str,
        edges: Iterable[EdgeRecord],
        node_id_map: Dict[str, Tuple[str, str]],
    ) -> None:
        emit_edges(
            self.conn,
            self._store,
            snapshot_id,
            edges,
            node_id_map,
            self.structural_cache,
        )

    def _lookup_structural_id(
        self,
        language: str,
        node_type: str,
        qualified_name: str,
        local_map: Dict[str, Tuple[str, str]],
    ) -> Optional[str]:
        return lookup_structural_id(
            language,
            node_type,
            qualified_name,
            local_map,
            self.structural_cache,
        )

    def _node_content_hash(
        self, node: SemanticNodeRecord, file_snapshot: FileSnapshot
    ) -> str:
        return node_content_hash(node, file_snapshot)

    def _merge_call_gate_diagnostics(self, stats: dict[str, object]) -> None:
        self.call_gate_diagnostics["identifiers_total"] = int(
            self.call_gate_diagnostics.get("identifiers_total", 0)
        ) + int(stats.get("identifiers_total", 0))
        self.call_gate_diagnostics["accepted_identifiers"] = int(
            self.call_gate_diagnostics.get("accepted_identifiers", 0)
        ) + int(stats.get("accepted_identifiers", 0))
        self.call_gate_diagnostics["dropped_identifiers"] = int(
            self.call_gate_diagnostics.get("dropped_identifiers", 0)
        ) + int(stats.get("dropped_identifiers", 0))
        self.call_gate_diagnostics["resolver_accepted_assembler_dropped"] = int(
            self.call_gate_diagnostics.get("resolver_accepted_assembler_dropped", 0)
        ) + int(stats.get("resolver_accepted_assembler_dropped", 0))
        self.call_gate_diagnostics["dropped_by_resolver"] = int(
            self.call_gate_diagnostics.get("dropped_by_resolver", 0)
        ) + int(stats.get("dropped_by_resolver", 0))
        self._merge_counter_map(
            self.call_gate_diagnostics, "accepted_by_provenance", stats.get("accepted_by_provenance")
        )
        self._merge_counter_map(
            self.call_gate_diagnostics, "dropped_by_reason", stats.get("dropped_by_reason")
        )

    @staticmethod
    def _merge_counter_map(target: dict[str, object], key: str, source: object) -> None:
        if not isinstance(source, dict):
            return
        bucket = target.setdefault(key, {})
        if not isinstance(bucket, dict):
            bucket = {}
            target[key] = bucket
        for counter_key, value in source.items():
            name = str(counter_key)
            bucket[name] = int(bucket.get(name, 0)) + int(value)

    @staticmethod
    def _inc_counter_map(target: dict[str, object], key: str, entry: str | None) -> None:
        bucket = target.setdefault(key, {})
        if not isinstance(bucket, dict):
            bucket = {}
            target[key] = bucket
        label = str(entry or "unknown")
        bucket[label] = int(bucket.get(label, 0)) + 1


def _module_qname_ancestors(module_qname: str) -> set[str]:
    parts = [part for part in module_qname.split(".") if part]
    ancestors: set[str] = set()
    for end in range(len(parts) - 1, 0, -1):
        ancestors.add(".".join(parts[:end]))
    return ancestors
