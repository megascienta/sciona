# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Protocol, Tuple

from sciona.data_storage.artifact_db import read_status as artifact_read_status

from .db_adapter import (
    call_edge_count_by_id,
    graph_edges_for_ids,
    resolve_module_structural_ids,
    resolve_node_instance,
)
from .ground_truth import build_module_imports_by_prefix, edge_records_from_ground_truth
from .independent.contract_normalization import (
    module_name_from_file,
    normalization_is_scoped_consistent,
    normalize_scoped_calls,
)
from .independent.normalize import normalize_file_edges
from .independent.shared import EdgeRecord, FileParseResult
from .metrics import compare_edge_sets, compute_metrics
from .sampling import build_entities_from_db, sample_entities
from .reducer_queries import (
    get_callsite_index_payload,
    get_class_overview,
    get_dependency_edges_payload,
)


def _edge_key_tuple(edge: EdgeRecord) -> tuple[str, str, str | None]:
    return (edge.caller, edge.callee, edge.callee_qname)


def _expected_call_form_map(entity_qname: str, normalized_calls, expected_filtered) -> dict:
    expected_keys = {_edge_key_tuple(edge) for edge in expected_filtered}
    forms = {key: "direct" for key in expected_keys}
    by_caller: dict[str, list] = {}
    for edge in normalized_calls:
        if edge.caller != entity_qname:
            continue
        by_caller.setdefault(edge.caller, []).append(edge)
    for key in expected_keys:
        caller, callee, callee_qname = key
        candidates = []
        for candidate in by_caller.get(caller, []):
            same_qname = callee_qname and candidate.callee_qname == callee_qname
            same_terminal = (candidate.callee or "").strip() == (callee or "").strip()
            if same_qname or same_terminal:
                candidates.append(candidate)
        if not candidates:
            continue
        if any("." in (candidate.callee_text or "") for candidate in candidates):
            forms[key] = "member"
        else:
            forms[key] = "direct"
    return forms


def _call_form_metrics(expected_filtered, sciona_edges, form_map: dict) -> dict:
    from .independent.shared import match_edge

    buckets = {"direct": {"tp": 0, "fn": 0}, "member": {"tp": 0, "fn": 0}}
    for expected in expected_filtered:
        key = _edge_key_tuple(expected)
        form = form_map.get(key, "direct")
        matched = False
        for actual in sciona_edges:
            if actual.caller != expected.caller:
                continue
            if match_edge(actual.callee, actual.callee_qname, expected.callee, expected.callee_qname):
                matched = True
                break
        if matched:
            buckets[form]["tp"] += 1
        else:
            buckets[form]["fn"] += 1
    result: dict[str, dict] = {}
    for form in ("direct", "member"):
        tp = buckets[form]["tp"]
        fn = buckets[form]["fn"]
        den = tp + fn
        result[form] = {
            "tp": tp,
            "fn": fn,
            "recall": (tp / den) if den else None,
        }
    return result


def _reason_recall_metrics(limitation_edges_by_reason: dict, sciona_edges) -> dict:
    from .independent.shared import match_edge

    result: dict[str, dict] = {}
    for reason, edges in (limitation_edges_by_reason or {}).items():
        tp = 0
        fn = 0
        for expected in edges:
            matched = False
            for actual in sciona_edges:
                if actual.caller != expected.caller:
                    continue
                if match_edge(actual.callee, actual.callee_qname, expected.callee, expected.callee_qname):
                    matched = True
                    break
            if matched:
                tp += 1
            else:
                fn += 1
        den = tp + fn
        result[reason] = {"tp": tp, "fn": fn, "recall": (tp / den) if den else None}
    return result


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
    return EdgeRecord(caller=caller, callee=callee or "", callee_qname=callee_qname)


def edge_record_from_import(edge: dict) -> EdgeRecord:
    caller = edge.get("from_module_qualified_name") or ""
    callee = edge.get("to_module_qualified_name") or ""
    return EdgeRecord(caller=caller, callee=callee, callee_qname=callee)


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


def build_normalized_edge_maps(
    repo_root: Path,
    independent_results: Dict[str, FileParseResult],
) -> Tuple[Dict[str, Tuple[List[object], List[object]]], dict, bool]:
    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]] = {}
    scoped_normalization_ok = True
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
        normalized_calls = normalize_scoped_calls(
            normalized_calls,
            language=file_result.language,
            module_scope=file_result.module_qualified_name,
        )
        if not normalization_is_scoped_consistent(normalized_calls):
            scoped_normalization_ok = False
        normalized_edge_map[file_result.file_path] = (normalized_calls, normalized_imports)
    module_imports_by_prefix = build_module_imports_by_prefix(
        independent_results, normalized_edge_map
    )
    return normalized_edge_map, module_imports_by_prefix, scoped_normalization_ok


def coverage_by_language(independent_results: Dict[str, FileParseResult]) -> Dict[str, dict]:
    coverage: Dict[str, dict] = {}
    for result in independent_results.values():
        language = result.language or "unknown"
        stats = coverage.setdefault(language, {"files_total": 0, "files_parsed": 0})
        stats["files_total"] += 1
        if result.parse_ok:
            stats["files_parsed"] += 1
    return coverage


def evaluate_entities(
    sampled,
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]],
    module_imports_by_prefix: dict,
    module_names: set[str],
    call_resolution: dict,
    contract: dict,
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
            contract,
            repo_root,
            repo_prefix,
            local_packages,
        )
        out_of_contract_meta.extend(out_meta)
        reducer_payloads, reducer_edges, reducer_error = reducer_source.get_edges(entity)
        _, db_edges, db_error = db_source.get_edges(entity)

        metrics_reducer_vs_db = None
        metrics_reducer_vs_contract = None
        metrics_db_vs_contract = None
        class_truth_unreliable = bool(gt_diagnostics.get("class_truth_unreliable"))
        if not reducer_error and not db_error:
            metrics_reducer_vs_db = compare_edge_sets(db_edges, reducer_edges)
        if (
            file_result.parse_ok
            and not db_error
            and not (entity.kind == "class" and class_truth_unreliable)
        ):
            metrics_db_vs_contract = compute_metrics(expected_filtered, [], db_edges)
        if (
            file_result.parse_ok
            and not reducer_error
            and not (entity.kind == "class" and class_truth_unreliable)
        ):
            metrics_reducer_vs_contract = compute_metrics(
                expected_filtered, out_of_contract, reducer_edges
            )
        rows.append(
            {
                "entity": entity.qualified_name,
                "language": entity.language,
                "kind": entity.kind,
                "file_path": entity.file_path,
                "module_qualified_name": entity.module_qualified_name,
                "metrics_reducer_vs_db": asdict(metrics_reducer_vs_db)
                if metrics_reducer_vs_db
                else None,
                "metrics_reducer_vs_contract": asdict(
                    metrics_reducer_vs_contract
                )
                if metrics_reducer_vs_contract
                else None,
                "metrics_db_vs_contract": asdict(metrics_db_vs_contract)
                if metrics_db_vs_contract
                else None,
                "contract_truth_edges": [asdict(edge) for edge in expected_filtered],
            }
        )
        if progress_handle:
            progress_handle.advance(1)
    if progress_handle:
        progress_handle.close()
    return rows, out_of_contract_meta
