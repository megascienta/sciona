# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Protocol, Tuple

from sciona.data_storage.artifact_db import read_status as artifact_read_status
from sciona.code_analysis.tools.call_extraction_queries import normalize_call_identifiers

from .db_adapter import (
    call_edge_count_by_id,
    graph_edges_for_ids,
    resolve_module_structural_ids,
    resolve_node_instance,
)
from .ground_truth import build_module_imports_by_prefix, edge_records_from_ground_truth
from .call_contract import resolve_call_in_contract
from .independent.contract_normalization import (
    module_name_from_file,
)
from .independent.normalize import normalize_file_edges
from .independent.shared import (
    EdgeRecord,
    FileParseResult,
    dedupe_edge_records,
)
from .metrics import compute_set_metrics
from .sampling import build_entities_from_db, sample_entities
from .reducer_queries import (
    get_callsite_index_payload,
    get_class_overview,
    get_dependency_edges_payload,
)


def _filter_core_edges_in_contract(
    *,
    entity,
    edges: list[EdgeRecord],
    call_resolution: dict,
    module_names: set[str],
) -> list[EdgeRecord]:
    if not edges:
        return []
    if entity.kind == "module":
        return dedupe_edge_records(
            [
                edge
                for edge in edges
                if (edge.callee_qname or edge.callee) in module_names
            ]
        )

    if entity.kind == "class":
        return dedupe_edge_records(edges)

    caller_qname = entity.qualified_name
    caller_module = entity.module_qualified_name
    filtered: list[EdgeRecord] = []
    module_lookup = call_resolution.get("module_lookup", {}) if call_resolution else {}
    for edge in edges:
        edge_for_resolution = edge
        # Reducer qname hints can be stale/non-canonical in some repos; if unknown,
        # discard the hint and resolve from stable identifiers instead of dropping.
        if edge.callee_qname and edge.callee_qname not in module_lookup:
            edge_for_resolution = EdgeRecord(
                caller=edge.caller,
                callee=edge.callee,
                callee_qname=None,
                provenance=edge.provenance,
            )
        resolved = resolve_call_in_contract(
            edge=edge_for_resolution,
            caller_qname=caller_qname,
            caller_module=caller_module,
            call_resolution=call_resolution,
        )
        if not resolved:
            continue
        filtered.append(
            EdgeRecord(
                caller=edge.caller,
                callee=resolved.split(".")[-1],
                callee_qname=resolved,
                provenance="core_contract",
            )
        )
    return dedupe_edge_records(filtered)


def module_qname_from_entity(entity) -> str:
    parts = entity.qualified_name.split(".")
    if entity.kind == "module":
        return entity.qualified_name
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return entity.qualified_name


def enrich_entities_with_db(entities, resolver, progress_handle=None) -> None:
    for entity in entities:
        resolved = resolver.resolve_node_instance(entity.qualified_name, entity.kind)
        if not resolved:
            if progress_handle:
                progress_handle.advance(1)
            continue
        resolved_path = resolved.get("file_path")
        if resolved_path:
            entity.file_path = resolved_path
        resolved_start = resolved.get("start_line")
        if resolved_start is not None:
            entity.start_line = resolved_start
        resolved_end = resolved.get("end_line")
        if resolved_end is not None:
            entity.end_line = resolved_end
        resolved_lang = resolved.get("language")
        if resolved_lang:
            entity.language = resolved_lang
        if progress_handle:
            progress_handle.advance(1)
    if progress_handle:
        progress_handle.close()


def edge_record_from_call(edge: dict, fallback_caller: str) -> EdgeRecord:
    caller = edge.get("caller_qualified_name") or fallback_caller
    callee_qname = edge.get("callee_qualified_name")
    callee = edge.get("callee_identifier") or edge.get("callee_name")
    if not callee and callee_qname:
        callee = callee_qname.split(".")[-1]
    return EdgeRecord(
        caller=caller,
        callee=callee or "",
        callee_qname=callee_qname,
        provenance="sciona_reducer",
    )


def edge_record_from_import(edge: dict) -> EdgeRecord:
    caller = edge.get("from_module_qualified_name") or ""
    callee = edge.get("to_module_qualified_name") or ""
    return EdgeRecord(
        caller=caller,
        callee=callee,
        callee_qname=callee,
        provenance="sciona_reducer",
    )


def canonical_module_name(repo_root: Path, file_result: FileParseResult) -> str:
    if not file_result.file_path:
        return file_result.module_qualified_name
    try:
        return module_name_from_file(
            repo_root=repo_root,
            file_path=file_result.file_path,
            language=(file_result.language or "").lower(),
        )
    except Exception:
        return file_result.module_qualified_name


def get_file_module_map(entities, resolver) -> Tuple[Dict[str, dict], Dict[str, str]]:
    mapping: Dict[str, dict] = {}
    errors: Dict[str, str] = {}
    for entity in entities:
        file_path = entity.file_path
        module_qname = entity.module_qualified_name or module_qname_from_entity(entity)
        if not file_path:
            resolved = resolver.resolve_node_instance(entity.qualified_name, entity.kind)
            if resolved and resolved.get("file_path"):
                file_path = resolved.get("file_path")
        if not file_path:
            errors[entity.qualified_name] = "missing file_path"
            continue
        mapping[file_path] = {
            "file_path": file_path,
            "module_qualified_name": module_qname,
            "language": entity.language,
        }
    return mapping, errors


def build_parse_file_map(
    sampled,
    file_map: Dict[str, dict],
    module_entries: List[dict],
) -> Dict[str, dict]:
    parse_map = dict(file_map)
    for entity in sampled:
        if entity.kind != "module":
            continue
        prefix = entity.qualified_name
        for entry in module_entries:
            module_name = entry.get("module_qualified_name") or entry.get("qualified_name")
            if not module_name:
                continue
            if module_name == prefix or module_name.startswith(f"{prefix}."):
                path = entry.get("path") or entry.get("file_path")
                if not path:
                    continue
                parse_map.setdefault(
                    path,
                    {
                        "file_path": path,
                        "module_qualified_name": module_name,
                        "language": entry.get("language") or entity.language,
                    },
                )
    return parse_map


class EdgeSource(Protocol):
    def get_edges(self, entity) -> Tuple[Dict[str, object], List[EdgeRecord], str | None]:
        ...


class ResolverCache:
    def __init__(self, core_conn, snapshot_id: str) -> None:
        self._core_conn = core_conn
        self._snapshot_id = snapshot_id
        self._node_instance_cache: Dict[Tuple[str, str], dict | None] = {}
        self._module_ids_cache: Dict[str, List[str]] = {}

    def resolve_node_instance(self, qualified_name: str, kind: str) -> dict | None:
        key = (qualified_name, kind)
        if key in self._node_instance_cache:
            return self._node_instance_cache[key]
        resolved = resolve_node_instance(self._core_conn, self._snapshot_id, qualified_name, kind)
        self._node_instance_cache[key] = resolved
        return resolved

    def resolve_module_structural_ids(self, qualified_name: str) -> List[str]:
        if qualified_name in self._module_ids_cache:
            return self._module_ids_cache[qualified_name]
        module_ids = resolve_module_structural_ids(
            self._core_conn, self._snapshot_id, qualified_name
        )
        self._module_ids_cache[qualified_name] = module_ids or []
        return self._module_ids_cache[qualified_name]


class ReducerEdgeSource:
    def __init__(self, conn, repo_root: Path, snapshot_id: str) -> None:
        self._conn = conn
        self._repo_root = repo_root
        self._snapshot_id = snapshot_id

    def get_edges(self, entity) -> Tuple[Dict[str, object], List[EdgeRecord], str | None]:
        try:
            payloads: Dict[str, object] = {}
            edges: List[EdgeRecord] = []
            if entity.kind == "module":
                dep_payload = get_dependency_edges_payload(
                    self._snapshot_id,
                    self._conn,
                    self._repo_root,
                    entity.qualified_name,
                )
                for edge in dep_payload.get("edges", []) or []:
                    edges.append(edge_record_from_import(edge))
                payloads["dependency_edges"] = dep_payload
                return payloads, edges, None

            if entity.kind == "class":
                class_id = entity.structural_id or entity.qualified_name
                class_payload = get_class_overview(
                    self._snapshot_id, self._conn, self._repo_root, class_id
                )
                for method in class_payload.get("methods", []) or []:
                    method_qname = method.get("qualified_name")
                    if not method_qname:
                        continue
                    edges.append(
                        EdgeRecord(
                            caller=entity.qualified_name,
                            callee=method_qname.split(".")[-1],
                            callee_qname=method_qname,
                            provenance="sciona_reducer",
                        )
                    )
                payloads["class_overview"] = class_payload
                return payloads, edges, None

            if entity.kind == "function":
                call_payload = get_callsite_index_payload(
                    self._snapshot_id,
                    self._conn,
                    self._repo_root,
                    function_id=entity.qualified_name,
                )
                for edge in call_payload.get("edges", []) or []:
                    edges.append(edge_record_from_call(edge, entity.qualified_name))
                payloads["callsite_index"] = call_payload
                return payloads, edges, None

            if entity.kind == "method":
                call_payload = get_callsite_index_payload(
                    self._snapshot_id,
                    self._conn,
                    self._repo_root,
                    method_id=entity.qualified_name,
                )
                for edge in call_payload.get("edges", []) or []:
                    edges.append(edge_record_from_call(edge, entity.qualified_name))
                payloads["callsite_index"] = call_payload
                return payloads, edges, None
        except Exception as exc:
            return {}, [], str(exc)
        return {}, [], None


class DbEdgeSource:
    def __init__(self, core_conn, artifact_conn, snapshot_id: str, resolver: ResolverCache) -> None:
        self._core_conn = core_conn
        self._artifact_conn = artifact_conn
        self._snapshot_id = snapshot_id
        self._resolver = resolver
        self._error: str | None = None
        if self._artifact_conn is None:
            self._error = "artifact db not available"
        elif not artifact_read_status.rebuild_consistent_for_snapshot(
            self._artifact_conn, snapshot_id=self._snapshot_id
        ):
            self._error = "artifact graph not consistent for snapshot"

    def get_edges(self, entity) -> Tuple[Dict[str, object], List[EdgeRecord], str | None]:
        if self._error:
            return {}, [], self._error
        try:
            edges: List[EdgeRecord] = []
            if entity.kind == "module":
                module_ids = self._resolver.resolve_module_structural_ids(entity.qualified_name)
                if not module_ids:
                    raise RuntimeError("module structural_id not found")
                edges = graph_edges_for_ids(
                    self._artifact_conn,
                    self._core_conn,
                    self._snapshot_id,
                    module_ids,
                    ["IMPORTS_DECLARED"],
                )
                return {}, edges, None

            if entity.kind == "class":
                resolved = self._resolver.resolve_node_instance(entity.qualified_name, "class")
                if not resolved or not resolved.get("structural_id"):
                    raise RuntimeError("class structural_id not found")
                class_id = resolved["structural_id"]
                edges = graph_edges_for_ids(
                    self._artifact_conn,
                    self._core_conn,
                    self._snapshot_id,
                    [class_id],
                    ["DEFINES_METHOD"],
                )
                return {}, edges, None

            if entity.kind in {"function", "method"}:
                resolved = self._resolver.resolve_node_instance(entity.qualified_name, entity.kind)
                if not resolved or not resolved.get("structural_id"):
                    raise RuntimeError("callable structural_id not found")
                call_id = resolved["structural_id"]
                edges = graph_edges_for_ids(
                    self._artifact_conn,
                    self._core_conn,
                    self._snapshot_id,
                    [call_id],
                    ["CALLS"],
                )
                return {}, edges, None
        except Exception as exc:
            return {}, [], str(exc)
        return {}, [], None


def sample_entities_from_db(
    nodes,
    resolver,
    artifact_conn,
    total_nodes: int,
    seed: int,
    progress_factory=None,
):
    entities = build_entities_from_db(nodes)
    progress = None
    if progress_factory:
        progress = progress_factory("Enriching entities", len(entities))
    enrich_entities_with_db(entities, resolver, progress_handle=progress)
    callable_ids = [
        entity.structural_id
        for entity in entities
        if entity.structural_id and entity.kind in {"function", "method"}
    ]
    edge_counts = call_edge_count_by_id(artifact_conn, callable_ids)
    for entity in entities:
        if entity.kind in {"function", "method"}:
            entity.call_edge_count = edge_counts.get(entity.structural_id, 0)
    return sample_entities(entities, total_nodes, seed)


def prepare_parse_map(sampled, module_entries, resolver) -> Tuple[Dict[str, dict], Dict[str, str]]:
    file_map, overview_errors = get_file_module_map(sampled, resolver)
    parse_file_map = build_parse_file_map(sampled, file_map, module_entries)
    return parse_file_map, overview_errors


def _build_syntax_reference_edges(
    *,
    entity,
    file_result: FileParseResult,
    normalized_calls: List[object],
    normalized_imports: List[object],
    module_imports_by_prefix: dict[str, list[tuple[str, str, str, object]]],
) -> List[EdgeRecord]:
    syntax_edges: List[EdgeRecord] = []
    if entity.kind in {"function", "method"}:
        for edge in normalized_calls:
            if edge.caller != entity.qualified_name or edge.dynamic:
                continue
            if not edge.callee:
                continue
            syntax_edges.append(
                EdgeRecord(
                    caller=edge.caller,
                    callee=edge.callee,
                    callee_qname=None,
                    provenance="syntax_only",
                )
            )
        return dedupe_edge_records(syntax_edges)
    if entity.kind == "class":
        class_qname = entity.qualified_name
        for definition in file_result.defs:
            if definition.kind != "method":
                continue
            if "." not in definition.qualified_name:
                continue
            owner = definition.qualified_name.rsplit(".", 1)[0]
            if owner != class_qname:
                continue
            syntax_edges.append(
                EdgeRecord(
                    caller=class_qname,
                    callee=definition.qualified_name.rsplit(".", 1)[-1],
                    callee_qname=None,
                    provenance="syntax_only",
                )
            )
        return dedupe_edge_records(syntax_edges)
    if entity.kind == "module":
        entries = module_imports_by_prefix.get(entity.qualified_name, [])
        if entries:
            for module_name, _file_path, _language, edge in entries:
                if edge.dynamic:
                    continue
                target = (edge.target_module or "").strip()
                if not target:
                    continue
                syntax_edges.append(
                    EdgeRecord(
                        caller=module_name,
                        callee=target,
                        callee_qname=None,
                        provenance="syntax_only",
                    )
                )
            return dedupe_edge_records(syntax_edges)
        for edge in normalized_imports:
            if edge.dynamic:
                continue
            target = (edge.target_module or "").strip()
            if not target:
                continue
            syntax_edges.append(
                EdgeRecord(
                    caller=file_result.module_qualified_name,
                    callee=target,
                    callee_qname=None,
                    provenance="syntax_only",
                )
            )
        return dedupe_edge_records(syntax_edges)
    return []


def build_normalized_edge_maps(
    repo_root: Path,
    independent_results: Dict[str, FileParseResult],
) -> Tuple[Dict[str, Tuple[List[object], List[object]]], dict, bool]:
    def _definition_kind_index() -> dict[str, str]:
        index: dict[str, str] = {}
        for file_result in independent_results.values():
            for definition in file_result.defs:
                index[definition.qualified_name] = definition.kind
        return index

    def _core_normalize_calls_across_files(
        calls_by_file: Dict[str, List[object]],
    ) -> Dict[str, List[object]]:
        kind_index = _definition_kind_index()
        records: list[tuple[str, str, str, list[str]]] = []
        edge_refs: list[tuple[str, object]] = []
        for file_path, calls in calls_by_file.items():
            file_result = independent_results.get(file_path)
            language = str((file_result.language if file_result else "unknown") or "unknown").lower()
            for edge in calls:
                identifier = (edge.callee_qname or edge.callee or "").strip()
                if not identifier:
                    continue
                caller_kind = kind_index.get(edge.caller, "function")
                node_type = "method" if caller_kind == "method" else "function"
                records.append((language, edge.caller, node_type, [identifier]))
                edge_refs.append((file_path, edge))
        normalized = normalize_call_identifiers(records) if records else []
        normalized_by_edge = {
            id(edge_refs[idx][1]): normalized[idx][3][0] if normalized[idx][3] else ""
            for idx in range(len(edge_refs))
        }
        updated: Dict[str, List[object]] = {}
        for file_path, calls in calls_by_file.items():
            normalized_calls: list[object] = []
            for edge in calls:
                normalized_identifier = normalized_by_edge.get(id(edge))
                if normalized_identifier is None or not normalized_identifier:
                    normalized_calls.append(edge)
                    continue
                if "." in normalized_identifier:
                    normalized_calls.append(
                        type(edge)(
                            caller=edge.caller,
                            callee=normalized_identifier.rsplit(".", 1)[-1],
                            callee_qname=normalized_identifier,
                            dynamic=edge.dynamic,
                            callee_text=edge.callee_text,
                            provenance=edge.provenance,
                        )
                    )
                else:
                    normalized_calls.append(
                        type(edge)(
                            caller=edge.caller,
                            callee=normalized_identifier,
                            callee_qname=None,
                            dynamic=edge.dynamic,
                            callee_text=edge.callee_text,
                            provenance=edge.provenance,
                        )
                    )
            updated[file_path] = normalized_calls
        return updated

    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]] = {}
    calls_by_file: Dict[str, List[object]] = {}
    imports_by_file: Dict[str, List[object]] = {}
    for file_result in independent_results.values():
        canonical_module = canonical_module_name(repo_root, file_result)
        if canonical_module:
            file_result.module_qualified_name = canonical_module
        normalized_calls, normalized_imports = normalize_file_edges(
            file_result.module_qualified_name,
            file_result.call_edges,
            file_result.import_edges,
            language=file_result.language,
        )
        calls_by_file[file_result.file_path] = normalized_calls
        imports_by_file[file_result.file_path] = normalized_imports
    normalized_calls_by_file = _core_normalize_calls_across_files(calls_by_file)
    for file_path in calls_by_file:
        normalized_edge_map[file_path] = (
            normalized_calls_by_file.get(file_path, calls_by_file[file_path]),
            imports_by_file.get(file_path, []),
        )
    module_imports_by_prefix = build_module_imports_by_prefix(
        independent_results, normalized_edge_map
    )
    return normalized_edge_map, module_imports_by_prefix, True


def evaluate_entities(
    sampled,
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]],
    module_imports_by_prefix: dict,
    module_names: set[str],
    call_resolution: dict,
    repo_root: Path,
    repo_prefix: str,
    local_packages: set[str],
    reducer_source: EdgeSource,
    db_source: EdgeSource,
    progress_handle,
) -> Tuple[List[dict], List[dict]]:
    rows: List[dict] = []
    out_of_contract_meta: List[dict] = []
    for entity in sampled:
        file_result = independent_results.get(entity.file_path)
        if not file_result:
            if progress_handle:
                progress_handle.advance(1)
            continue
        normalized_calls, normalized_imports = normalized_edge_map.get(
            entity.file_path, ([], [])
        )
        (
            expected_filtered,
            full_truth,
            out_of_contract,
            out_meta,
            gt_diagnostics,
        ) = edge_records_from_ground_truth(
            file_result,
            normalized_calls,
            normalized_imports,
            module_imports_by_prefix,
            entity,
            module_names,
            call_resolution,
            repo_root,
            repo_prefix,
            local_packages,
        )
        out_of_contract_meta.extend(out_meta)
        _, reducer_edges, reducer_error = reducer_source.get_edges(entity)
        _, db_edges, db_error = db_source.get_edges(entity)
        reducer_edges_contract = _filter_core_edges_in_contract(
            entity=entity,
            edges=reducer_edges,
            call_resolution=call_resolution,
            module_names=module_names,
        )
        set_q1_reducer_vs_db = None
        set_q2_reducer_vs_independent_contract = None
        set_q2_reducer_vs_independent_syntax = None
        class_truth_unreliable = bool(gt_diagnostics.get("class_truth_unreliable"))
        syntax_reference_edges = _build_syntax_reference_edges(
            entity=entity,
            file_result=file_result,
            normalized_calls=normalized_calls,
            normalized_imports=normalized_imports,
            module_imports_by_prefix=module_imports_by_prefix,
        )
        if not reducer_error and not db_error:
            set_q1_reducer_vs_db = compute_set_metrics(db_edges, reducer_edges)
        if (
            file_result.parse_ok
            and not reducer_error
            and not (entity.kind == "class" and class_truth_unreliable)
        ):
            set_q2_reducer_vs_independent_contract = compute_set_metrics(
                reducer_edges_contract, expected_filtered
            )
        if file_result.parse_ok and not reducer_error:
            set_q2_reducer_vs_independent_syntax = compute_set_metrics(
                reducer_edges_contract, syntax_reference_edges
            )
        rows.append(
            {
                "entity": entity.qualified_name,
                "language": entity.language,
                "kind": entity.kind,
                "file_path": entity.file_path,
                "module_qualified_name": entity.module_qualified_name,
                "set_q1_reducer_vs_db": asdict(set_q1_reducer_vs_db)
                if set_q1_reducer_vs_db
                else None,
                "set_q2_reducer_vs_independent_contract": asdict(
                    set_q2_reducer_vs_independent_contract
                )
                if set_q2_reducer_vs_independent_contract
                else None,
                "set_q2_reducer_vs_independent_syntax": asdict(
                    set_q2_reducer_vs_independent_syntax
                )
                if set_q2_reducer_vs_independent_syntax
                else None,
                "basket2_edges": [asdict(edge) for edge in out_of_contract],
                "q2_filtering_stats": {
                    "reference_in_contract_count": len(expected_filtered),
                    "excluded_out_of_scope_count": int(
                        gt_diagnostics.get("excluded_out_of_scope_count") or 0
                    ),
                    "excluded_limitation_count": int(
                        gt_diagnostics.get("included_limitation_count") or 0
                    ),
                    "excluded_total_count": int(
                        (gt_diagnostics.get("excluded_out_of_scope_count") or 0)
                        + (gt_diagnostics.get("included_limitation_count") or 0)
                    ),
                    "excluded_out_of_scope_by_reason": dict(
                        gt_diagnostics.get("excluded_out_of_scope_by_reason") or {}
                    ),
                    "excluded_limitation_by_reason": dict(
                        gt_diagnostics.get("included_limitation_by_reason") or {}
                    ),
                },
                "q2_ground_truth_diagnostics": {
                    "class_truth_unreliable": (
                        bool(gt_diagnostics.get("class_truth_unreliable"))
                        if gt_diagnostics.get("class_truth_unreliable") is not None
                        else None
                    ),
                    "class_match_strategy": gt_diagnostics.get("class_match_strategy"),
                    "class_candidate_count": int(gt_diagnostics.get("class_candidate_count") or 0),
                    "class_truth_method_count": int(gt_diagnostics.get("class_truth_method_count") or 0),
                    "strict_contract_candidate_count_histogram": dict(
                        gt_diagnostics.get("strict_contract_candidate_count_histogram") or {}
                    ),
                },
            }
        )
        if progress_handle:
            progress_handle.advance(1)
    if progress_handle:
        progress_handle.close()
    return rows, out_of_contract_meta
