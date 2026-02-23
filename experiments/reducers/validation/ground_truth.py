# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict, List, Tuple

from . import config
from .call_contract import resolve_call_in_contract
from .import_contract import resolve_import_contract
from .independent.shared import EdgeRecord, FileParseResult, dedupe_edge_records
from .out_of_contract import (
    classify_call_reason,
    classify_import_reason,
    standard_call_names,
)


def build_module_imports_by_prefix(
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, tuple[list[object], list[object]]],
) -> Dict[str, List[Tuple[str, str, str, object]]]:
    module_imports_by_prefix: Dict[str, List[Tuple[str, str, str, object]]] = {}
    for file_result in independent_results.values():
        module_name = file_result.module_qualified_name
        module_parts = module_name.split(".") if module_name else []
        normalized = normalized_edge_map.get(file_result.file_path)
        if not normalized or not normalized[1]:
            continue
        for edge in normalized[1]:
            for i in range(1, len(module_parts) + 1):
                prefix = ".".join(module_parts[:i])
                module_imports_by_prefix.setdefault(prefix, []).append(
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
    contract: dict,
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
        "limitation_edges_high_conf": [],
        "limitation_edges_full": [],
    }
    standard_calls = standard_call_names(contract)
    policy = config.EXPANDED_TRUTH_POLICY
    excluded_reasons = set(policy.get("scope_exclusions") or [])
    high_conf_reasons = set((policy.get("confidence_tiers") or {}).get("high") or [])
    low_conf_reasons = set((policy.get("confidence_tiers") or {}).get("low") or [])

    def _register_limitation_edge(reason: str, record: EdgeRecord) -> None:
        if reason in excluded_reasons:
            diagnostics["excluded_out_of_scope_count"] += 1
            excluded = diagnostics.setdefault("excluded_out_of_scope_by_reason", {})
            excluded[reason] = int(excluded.get(reason, 0)) + 1
            return
        diagnostics["included_limitation_count"] += 1
        included = diagnostics.setdefault("included_limitation_by_reason", {})
        included[reason] = int(included.get(reason, 0)) + 1
        out_of_contract.append(record)
        if reason in high_conf_reasons:
            diagnostics["limitation_edges_high_conf"].append(record)
            diagnostics["limitation_edges_full"].append(record)
            return
        if reason in low_conf_reasons:
            diagnostics["limitation_edges_full"].append(record)
            return

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
                contract,
                module_names,
                repo_root,
                repo_prefix,
                local_packages,
            )
            record = EdgeRecord(
                caller=caller,
                callee=resolved or raw_target,
                callee_qname=resolved,
            )
            if edge.dynamic or not resolved:
                reason = classify_import_reason(
                    raw_target=raw_target,
                    resolved=resolved,
                    language=language,
                    repo_prefix=repo_prefix,
                )
                _register_limitation_edge(reason, record)
                if reason not in excluded_reasons:
                    out_of_contract_meta.append(
                        {
                            "edge_type": "import",
                            "language": language,
                            "reason": reason,
                        }
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
                    contract,
                    module_names,
                    repo_root,
                    repo_prefix,
                    local_packages,
                )
                record = EdgeRecord(
                    caller=caller,
                    callee=resolved or raw_target,
                    callee_qname=resolved,
                )
                if edge.dynamic or not resolved:
                    reason = classify_import_reason(
                        raw_target=raw_target,
                        resolved=resolved,
                        language=file_result.language,
                        repo_prefix=repo_prefix,
                    )
                    _register_limitation_edge(reason, record)
                    if reason not in excluded_reasons:
                        out_of_contract_meta.append(
                            {
                                "edge_type": "import",
                                "language": file_result.language,
                                "reason": reason,
                            }
                        )
                else:
                    expected_filtered.append(record)
                    full_truth.append(record)
        diagnostics["limitation_edges_high_conf"] = dedupe_edge_records(
            diagnostics["limitation_edges_high_conf"]
        )
        diagnostics["limitation_edges_full"] = dedupe_edge_records(
            diagnostics["limitation_edges_full"]
        )
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
            )
            expected_filtered.append(record)
            full_truth.append(record)
        diagnostics["class_truth_method_count"] = len(expected_filtered)
        diagnostics["limitation_edges_high_conf"] = dedupe_edge_records(
            diagnostics["limitation_edges_high_conf"]
        )
        diagnostics["limitation_edges_full"] = dedupe_edge_records(
            diagnostics["limitation_edges_full"]
        )
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
        resolved_callee_qname = resolve_call_in_contract(
            edge=edge,
            caller_qname=entity.qualified_name,
            caller_module=entity.module_qualified_name,
            call_resolution=call_resolution,
            contract=contract,
        )
        full_record = EdgeRecord(
            caller=edge.caller,
            callee=edge.callee,
            callee_qname=edge.callee_qname,
        )
        if (
            not edge.dynamic
            and resolved_callee_qname
            and (edge.callee or "").strip() not in standard_calls
        ):
            resolved_record = EdgeRecord(
                caller=edge.caller,
                callee=edge.callee or resolved_callee_qname.split(".")[-1],
                callee_qname=resolved_callee_qname,
            )
            expected_filtered.append(resolved_record)
            full_truth.append(resolved_record)
        else:
            reason = classify_call_reason(
                edge=edge,
                language=file_result.language,
                call_resolution=call_resolution,
                contract=contract,
            )
            _register_limitation_edge(reason, full_record)
            if reason not in excluded_reasons:
                out_of_contract_meta.append(
                    {
                        "edge_type": "call",
                        "language": file_result.language,
                        "reason": reason,
                    }
                )
    diagnostics["limitation_edges_high_conf"] = dedupe_edge_records(
        diagnostics["limitation_edges_high_conf"]
    )
    diagnostics["limitation_edges_full"] = dedupe_edge_records(
        diagnostics["limitation_edges_full"]
    )
    return (
        dedupe_edge_records(expected_filtered),
        dedupe_edge_records(full_truth),
        dedupe_edge_records(out_of_contract),
        out_of_contract_meta,
        diagnostics,
    )
