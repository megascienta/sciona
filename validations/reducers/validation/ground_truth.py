# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict, List, Tuple

from . import config
from .call_contract import resolve_call_in_contract_details
from .import_contract import likely_java_import_normalization_miss, resolve_import_contract
from .independent.shared import EdgeRecord, FileParseResult, dedupe_edge_records
from .out_of_contract import (
    classify_call_reason,
    classify_call_semantic_type,
    classify_import_reason,
    classify_import_semantic_type,
)


def build_module_imports_by_prefix(
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, tuple[list[object], list[object]]],
) -> Dict[str, List[Tuple[str, str, str, object]]]:
    module_imports_by_prefix: Dict[str, List[Tuple[str, str, str, object]]] = {}
    for file_result in independent_results.values():
        module_name = file_result.module_qualified_name
        if not module_name:
            continue
        normalized = normalized_edge_map.get(file_result.file_path)
        if not normalized or not normalized[1]:
            continue
        for edge in normalized[1]:
            module_imports_by_prefix.setdefault(module_name, []).append(
                (module_name, file_result.file_path, file_result.language, edge)
            )
    return module_imports_by_prefix


def edge_records_from_ground_truth(
    file_result: FileParseResult,
    normalized_calls,
    normalized_imports,
    module_imports_by_prefix: dict[str, list[tuple[str, str, str, object]]],
    entity,
    module_names: set[str],
    call_resolution: dict,
    repo_root,
    repo_prefix: str,
    local_packages: set[str],
) -> Tuple[List[EdgeRecord], List[EdgeRecord], List[EdgeRecord], List[dict], dict]:
    # Contract-first truth: only in-repo, contract-compatible edges.
    expected_filtered: List[EdgeRecord] = []
    full_truth: List[EdgeRecord] = []
    out_of_contract: List[EdgeRecord] = []
    out_of_contract_meta: List[dict] = []
    diagnostics: dict = {
        "class_has_methods": None,
        "class_match_strategy": None,
        "class_candidate_count": 0,
        "class_truth_method_count": 0,
        "class_truth_unreliable": None,
        "excluded_out_of_scope_count": 0,
        "included_limitation_count": 0,
        "excluded_out_of_scope_by_reason": {},
        "included_limitation_by_reason": {},
        "contract_exclusion_edges_full": [],
        "contract_exclusion_edges_by_reason": {},
        "independent_limitation_edges_full": [],
        "independent_limitation_edges_by_reason": {},
        "limitation_edges_high_conf": [],
        "limitation_edges_full": [],
        "limitation_edges_by_reason": {},
        "strict_contract_accepted_by_provenance": {},
        "strict_contract_candidate_count_histogram": {},
    }
    policy = config.EXPANDED_TRUTH_POLICY
    excluded_reasons = set(policy.get("scope_exclusions") or [])
    high_conf_reasons = set((policy.get("confidence_tiers") or {}).get("high") or [])
    low_conf_reasons = set((policy.get("confidence_tiers") or {}).get("low") or [])

    def _edge_key(record: EdgeRecord) -> tuple[str, str, str | None]:
        return (record.caller, record.callee, record.callee_qname)

    def _dedupe_preserve_order(edges: list[EdgeRecord]) -> list[EdgeRecord]:
        seen: set[tuple[str, str, str | None]] = set()
        ordered: list[EdgeRecord] = []
        for record in edges:
            key = _edge_key(record)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(record)
        return ordered

    def _apply_basket_partition() -> None:
        nonlocal out_of_contract
        contract_keys = {_edge_key(record) for record in expected_filtered}
        exclusion_edges = _dedupe_preserve_order(
            diagnostics.get("contract_exclusion_edges_full") or []
        )
        exclusion_edges = [
            record for record in exclusion_edges if _edge_key(record) not in contract_keys
        ]
        exclusion_keys = {_edge_key(record) for record in exclusion_edges}

        limitation_edges = _dedupe_preserve_order(
            diagnostics.get("independent_limitation_edges_full") or []
        )
        limitation_edges = [
            record
            for record in limitation_edges
            if _edge_key(record) not in contract_keys
            and _edge_key(record) not in exclusion_keys
        ]
        limitation_keys = {_edge_key(record) for record in limitation_edges}

        diagnostics["contract_exclusion_edges_full"] = exclusion_edges
        diagnostics["independent_limitation_edges_full"] = limitation_edges
        out_of_contract = limitation_edges

        contract_by_reason = diagnostics.get("contract_exclusion_edges_by_reason") or {}
        diagnostics["contract_exclusion_edges_by_reason"] = {
            reason: [
                record for record in _dedupe_preserve_order(edges) if _edge_key(record) in exclusion_keys
            ]
            for reason, edges in contract_by_reason.items()
        }
        diagnostics["excluded_out_of_scope_by_reason"] = {
            reason: len(edges)
            for reason, edges in diagnostics["contract_exclusion_edges_by_reason"].items()
            if edges
        }
        diagnostics["excluded_out_of_scope_count"] = int(
            sum(diagnostics["excluded_out_of_scope_by_reason"].values())
        )
        independent_by_reason = diagnostics.get("independent_limitation_edges_by_reason") or {}
        diagnostics["independent_limitation_edges_by_reason"] = {
            reason: [
                record for record in _dedupe_preserve_order(edges) if _edge_key(record) in limitation_keys
            ]
            for reason, edges in independent_by_reason.items()
        }
        diagnostics["included_limitation_by_reason"] = {
            reason: len(edges)
            for reason, edges in diagnostics["independent_limitation_edges_by_reason"].items()
            if edges
        }
        diagnostics["included_limitation_count"] = int(
            sum(diagnostics["included_limitation_by_reason"].values())
        )
        limitation_by_reason = diagnostics.get("limitation_edges_by_reason") or {}
        diagnostics["limitation_edges_by_reason"] = {
            reason: [
                record for record in _dedupe_preserve_order(edges) if _edge_key(record) in limitation_keys
            ]
            for reason, edges in limitation_by_reason.items()
        }
        diagnostics["limitation_edges_high_conf"] = [
            record
            for record in _dedupe_preserve_order(
                diagnostics.get("limitation_edges_high_conf") or []
            )
            if _edge_key(record) in limitation_keys
        ]
        diagnostics["limitation_edges_full"] = [
            record
            for record in _dedupe_preserve_order(
                diagnostics.get("limitation_edges_full") or []
            )
            if _edge_key(record) in limitation_keys
        ]

    def _register_limitation_edge(reason: str, record: EdgeRecord) -> None:
        if reason in excluded_reasons:
            diagnostics["excluded_out_of_scope_count"] += 1
            excluded = diagnostics.setdefault("excluded_out_of_scope_by_reason", {})
            excluded[reason] = int(excluded.get(reason, 0)) + 1
            diagnostics.setdefault("contract_exclusion_edges_full", []).append(record)
            diagnostics.setdefault("contract_exclusion_edges_by_reason", {}).setdefault(
                reason, []
            ).append(record)
            return
        diagnostics["included_limitation_count"] += 1
        included = diagnostics.setdefault("included_limitation_by_reason", {})
        included[reason] = int(included.get(reason, 0)) + 1
        out_of_contract.append(record)
        diagnostics.setdefault("independent_limitation_edges_full", []).append(record)
        diagnostics.setdefault("independent_limitation_edges_by_reason", {}).setdefault(
            reason, []
        ).append(record)
        diagnostics.setdefault("limitation_edges_by_reason", {}).setdefault(reason, []).append(
            record
        )
        if reason in high_conf_reasons:
            diagnostics["limitation_edges_high_conf"].append(record)
            diagnostics["limitation_edges_full"].append(record)
            return
        if reason in low_conf_reasons:
            diagnostics["limitation_edges_full"].append(record)
            return

    def _append_basket2_meta(
        *,
        record: EdgeRecord,
        edge_type: str,
        language: str,
        reason: str,
        semantic_type: str,
        entity_qname: str,
        entity_kind: str,
    ) -> None:
        if reason in excluded_reasons:
            return
        out_of_contract_meta.append(
            {
                "edge_type": edge_type,
                "language": language,
                "reason": reason,
                "semantic_type": semantic_type,
                "entity": entity_qname,
                "entity_kind": entity_kind,
                "caller": record.caller,
                "callee": record.callee,
                "callee_qname": record.callee_qname,
                "provenance": record.provenance,
            }
        )

    def _finalize_basket2_meta() -> None:
        limitation_keys = {_edge_key(record) for record in out_of_contract}
        filtered: list[dict] = []
        seen: set[tuple[str, str, str | None, str]] = set()
        for meta in out_of_contract_meta:
            key = (
                str(meta.get("caller") or ""),
                str(meta.get("callee") or ""),
                str(meta.get("callee_qname")) if meta.get("callee_qname") is not None else None,
            )
            if key not in limitation_keys:
                continue
            dedupe_key = (
                key[0],
                key[1],
                key[2],
                str(meta.get("reason") or ""),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            filtered.append(meta)
        out_of_contract_meta.clear()
        out_of_contract_meta.extend(filtered)

    def _finalize_diagnostics() -> None:
        diagnostics["limitation_edges_high_conf"] = dedupe_edge_records(
            diagnostics["limitation_edges_high_conf"]
        )
        diagnostics["limitation_edges_full"] = dedupe_edge_records(
            diagnostics["limitation_edges_full"]
        )
        by_reason = diagnostics.get("limitation_edges_by_reason") or {}
        diagnostics["limitation_edges_by_reason"] = {
            reason: dedupe_edge_records(edges)
            for reason, edges in by_reason.items()
        }
        diagnostics["contract_exclusion_edges_full"] = dedupe_edge_records(
            diagnostics["contract_exclusion_edges_full"]
        )
        contract_by_reason = diagnostics.get("contract_exclusion_edges_by_reason") or {}
        diagnostics["contract_exclusion_edges_by_reason"] = {
            reason: dedupe_edge_records(edges)
            for reason, edges in contract_by_reason.items()
        }
        diagnostics["excluded_out_of_scope_by_reason"] = {
            reason: len(edges)
            for reason, edges in diagnostics["contract_exclusion_edges_by_reason"].items()
        }
        diagnostics["excluded_out_of_scope_count"] = int(
            sum(diagnostics["excluded_out_of_scope_by_reason"].values())
        )
        diagnostics["independent_limitation_edges_full"] = dedupe_edge_records(
            diagnostics["independent_limitation_edges_full"]
        )
        independent_by_reason = diagnostics.get("independent_limitation_edges_by_reason") or {}
        diagnostics["independent_limitation_edges_by_reason"] = {
            reason: dedupe_edge_records(edges)
            for reason, edges in independent_by_reason.items()
        }
        diagnostics["included_limitation_by_reason"] = {
            reason: len(edges)
            for reason, edges in diagnostics["independent_limitation_edges_by_reason"].items()
        }
        diagnostics["included_limitation_count"] = int(
            sum(diagnostics["included_limitation_by_reason"].values())
        )
        _apply_basket_partition()
        _finalize_basket2_meta()

    if entity.kind == "module":
        entries = module_imports_by_prefix.get(entity.qualified_name, [])
        for module_name, file_path, language, edge in entries:
            caller = module_name
            raw_target = edge.target_module
            resolved = resolve_import_contract(
                raw_target,
                file_path,
                module_name,
                language,
                module_names,
                repo_root,
                repo_prefix,
                local_packages,
            )
            record = EdgeRecord(
                caller=caller,
                callee=resolved or raw_target,
                callee_qname=resolved,
                provenance=getattr(edge, "provenance", "syntax_raw"),
            )
            if edge.dynamic or not resolved:
                reason = classify_import_reason(
                    raw_target=raw_target,
                    resolved=resolved,
                    repo_prefix=repo_prefix,
                    dynamic=bool(edge.dynamic),
                    normalization_miss=(
                        language == "java"
                        and not resolved
                        and likely_java_import_normalization_miss(
                            raw_target=raw_target,
                            module_qname=module_name,
                            repo_prefix=repo_prefix,
                            module_names=module_names,
                        )
                    ),
                )
                _register_limitation_edge(reason, record)
                _append_basket2_meta(
                    record=record,
                    edge_type="import",
                    language=language,
                    reason=reason,
                    semantic_type=classify_import_semantic_type(
                        raw_target=raw_target,
                        reason=reason,
                    ),
                    entity_qname=entity.qualified_name,
                    entity_kind=entity.kind,
                )
            else:
                expected_filtered.append(record)
                full_truth.append(record)
        if not entries:
            for edge in normalized_imports:
                caller = file_result.module_qualified_name
                raw_target = edge.target_module
                resolved = resolve_import_contract(
                    raw_target,
                    file_result.file_path,
                    file_result.module_qualified_name,
                    file_result.language,
                    module_names,
                    repo_root,
                    repo_prefix,
                    local_packages,
                )
                record = EdgeRecord(
                    caller=caller,
                    callee=resolved or raw_target,
                    callee_qname=resolved,
                    provenance=getattr(edge, "provenance", "syntax_raw"),
                )
                if edge.dynamic or not resolved:
                    reason = classify_import_reason(
                        raw_target=raw_target,
                        resolved=resolved,
                        repo_prefix=repo_prefix,
                        dynamic=bool(edge.dynamic),
                        normalization_miss=(
                            file_result.language == "java"
                            and not resolved
                            and likely_java_import_normalization_miss(
                                raw_target=raw_target,
                                module_qname=file_result.module_qualified_name,
                                repo_prefix=repo_prefix,
                                module_names=module_names,
                            )
                        ),
                    )
                    _register_limitation_edge(reason, record)
                    _append_basket2_meta(
                        record=record,
                        edge_type="import",
                        language=file_result.language,
                        reason=reason,
                        semantic_type=classify_import_semantic_type(
                            raw_target=raw_target,
                            reason=reason,
                        ),
                        entity_qname=entity.qualified_name,
                        entity_kind=entity.kind,
                    )
                else:
                    expected_filtered.append(record)
                    full_truth.append(record)
        _finalize_diagnostics()
        return (
            dedupe_edge_records(expected_filtered),
            dedupe_edge_records(full_truth),
            dedupe_edge_records(out_of_contract),
            out_of_contract_meta,
            diagnostics,
        )

    if entity.kind == "class":
        class_qname = entity.qualified_name
        matched_class = None
        class_match_strategy = "none"
        diagnostics["class_truth_unreliable"] = False

        class_candidates = [
            definition for definition in file_result.defs if definition.kind == "class"
        ]
        diagnostics["class_candidate_count"] = len(class_candidates)

        def _simple_name(qualified_name: str, default: str | None) -> str:
            if default:
                return default
            return qualified_name.rsplit(".", 1)[-1]

        def _enclosing_class(qualified_name: str, default: str | None) -> str | None:
            if default:
                return default
            if "." not in qualified_name:
                return None
            parent = qualified_name.rsplit(".", 1)[0]
            return parent or None

        # 1) strict exact qname
        for definition in class_candidates:
            if definition.qualified_name == entity.qualified_name:
                matched_class = definition
                class_match_strategy = "exact_qname"
                break

        entity_start = getattr(entity, "start_line", None)
        entity_end = getattr(entity, "end_line", None)
        entity_simple = entity.qualified_name.rsplit(".", 1)[-1]
        entity_parent = (
            entity.qualified_name.rsplit(".", 1)[0]
            if "." in entity.qualified_name
            else None
        )

        if matched_class is None:
            same_simple = [
                definition
                for definition in class_candidates
                if _simple_name(definition.qualified_name, definition.simple_name)
                == entity_simple
            ]
            if len(same_simple) == 1:
                matched_class = same_simple[0]
                class_match_strategy = "simple_unique"
            elif same_simple:
                same_parent = [
                    definition
                    for definition in same_simple
                    if _enclosing_class(
                        definition.qualified_name,
                        definition.enclosing_class_qname,
                    )
                    == entity_parent
                ]
                if len(same_parent) == 1:
                    matched_class = same_parent[0]
                    class_match_strategy = "parent_and_simple"
                else:
                    span_candidates = same_parent or same_simple
                    if entity_start and entity_end:
                        overlapping = [
                            definition
                            for definition in span_candidates
                            if not (
                                definition.end_line < entity_start
                                or definition.start_line > entity_end
                            )
                        ]
                        if len(overlapping) == 1:
                            matched_class = overlapping[0]
                            class_match_strategy = "line_span_overlap"
                        elif len(overlapping) > 1:
                            class_match_strategy = "ambiguous"
                    else:
                        class_match_strategy = "ambiguous"

        if matched_class is not None:
            class_qname = matched_class.qualified_name
        diagnostics["class_match_strategy"] = class_match_strategy
        diagnostics["class_truth_unreliable"] = matched_class is None

        def _direct_owner(method_qname: str) -> str:
            if "." not in method_qname:
                return ""
            return method_qname.rsplit(".", 1)[0]

        diagnostics["class_has_methods"] = any(
            definition.kind == "method"
            and _direct_owner(definition.qualified_name) == class_qname
            for definition in file_result.defs
        )
        for definition in file_result.defs:
            if definition.kind != "method":
                continue
            if _direct_owner(definition.qualified_name) != class_qname:
                continue
            callee_qname = definition.qualified_name
            record = EdgeRecord(
                caller=entity.qualified_name,
                callee=callee_qname.split(".")[-1],
                callee_qname=callee_qname,
                provenance="syntax_raw",
            )
            expected_filtered.append(record)
            full_truth.append(record)
        diagnostics["class_truth_method_count"] = len(expected_filtered)
        _finalize_diagnostics()
        return (
            dedupe_edge_records(expected_filtered),
            dedupe_edge_records(full_truth),
            dedupe_edge_records(out_of_contract),
            out_of_contract_meta,
            diagnostics,
        )

    for edge in normalized_calls:
        if edge.caller != entity.qualified_name:
            continue
        call_decision = resolve_call_in_contract_details(
            edge=edge,
            caller_qname=entity.qualified_name,
            caller_module=entity.module_qualified_name,
            call_resolution=call_resolution,
        )
        resolved_callee_qname = call_decision.callee_qname
        if call_decision.accepted_provenance:
            accepted = diagnostics.setdefault("strict_contract_accepted_by_provenance", {})
            accepted[call_decision.accepted_provenance] = int(
                accepted.get(call_decision.accepted_provenance, 0)
            ) + 1
        if call_decision.candidate_count >= 0:
            histogram = diagnostics.setdefault(
                "strict_contract_candidate_count_histogram", {}
            )
            bucket = str(call_decision.candidate_count)
            histogram[bucket] = int(histogram.get(bucket, 0)) + 1
        full_record = EdgeRecord(
            caller=edge.caller,
            callee=edge.callee,
            callee_qname=edge.callee_qname,
            provenance=getattr(edge, "provenance", "syntax_raw"),
        )
        module_lookup: dict[str, str] = call_resolution.get("module_lookup", {})
        raw_callee_qname = (edge.callee_qname or "").strip()
        unresolved_placeholder_hint = bool(
            raw_callee_qname
            and raw_callee_qname not in module_lookup
            and "." in raw_callee_qname
        )
        if (
            not edge.dynamic
            and resolved_callee_qname
            and not unresolved_placeholder_hint
        ):
            resolved_record = EdgeRecord(
                caller=edge.caller,
                callee=edge.callee or resolved_callee_qname.split(".")[-1],
                callee_qname=resolved_callee_qname,
                provenance=(
                    f"contract:{call_decision.accepted_provenance}"
                    if call_decision.accepted_provenance
                    else getattr(edge, "provenance", "syntax_raw")
                ),
            )
            expected_filtered.append(resolved_record)
            full_truth.append(resolved_record)
        else:
            call_reason = classify_call_reason(
                edge=edge,
                language=file_result.language,
                call_resolution=call_resolution,
                dropped_reason=call_decision.dropped_reason,
            )
            _register_limitation_edge(call_reason, full_record)
            _append_basket2_meta(
                record=full_record,
                edge_type="call",
                language=file_result.language,
                reason=call_reason,
                semantic_type=classify_call_semantic_type(edge=edge, reason=call_reason),
                entity_qname=entity.qualified_name,
                entity_kind=entity.kind,
            )
    _finalize_diagnostics()
    return (
        dedupe_edge_records(expected_filtered),
        dedupe_edge_records(full_truth),
        dedupe_edge_records(out_of_contract),
        out_of_contract_meta,
        diagnostics,
    )
