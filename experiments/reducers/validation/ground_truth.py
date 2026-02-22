# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict, List, Tuple

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
    }
    standard_calls = standard_call_names(contract)

    def _skip_external(reason: str) -> bool:
        # External dependencies are outside SCIONA contract; exclude from truth/enrichment.
        return reason == "external"

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
                if _skip_external(reason):
                    continue
                out_of_contract.append(record)
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
                    if _skip_external(reason):
                        continue
                    out_of_contract.append(record)
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
        class_candidates = [
            definition for definition in file_result.defs if definition.kind == "class"
        ]
        diagnostics["class_candidate_count"] = len(class_candidates)
        for definition in file_result.defs:
            if definition.kind != "class":
                continue
            if definition.qualified_name == entity.qualified_name:
                matched_class = definition
                class_match_strategy = "exact_qname"
                break
        entity_start = getattr(entity, "start_line", None)
        entity_end = getattr(entity, "end_line", None)
        if matched_class is None and entity_start and entity_end:
            containing_exact = [
                definition
                for definition in file_result.defs
                if definition.kind == "class"
                and definition.start_line <= entity_start
                and definition.end_line >= entity_end
                and definition.qualified_name.startswith(
                    f"{entity.module_qualified_name}."
                )
            ]
            if containing_exact:
                containing_exact.sort(
                    key=lambda item: (
                        item.end_line - item.start_line,
                        item.qualified_name,
                    )
                )
                matched_class = containing_exact[0]
                class_match_strategy = "line_span"
        if matched_class is None:
            leaf = entity.qualified_name.rsplit(".", 1)[-1]
            same_leaf = [
                definition
                for definition in file_result.defs
                if definition.kind == "class"
                and definition.qualified_name.rsplit(".", 1)[-1] == leaf
                and (
                    definition.qualified_name == entity.qualified_name
                    or definition.qualified_name.startswith(f"{entity.module_qualified_name}.")
                )
            ]
            if len(same_leaf) == 1:
                matched_class = same_leaf[0]
                class_match_strategy = "scoped_leaf"
        if matched_class is not None:
            class_qname = matched_class.qualified_name
        diagnostics["class_match_strategy"] = class_match_strategy

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
            if _skip_external(reason):
                continue
            out_of_contract.append(full_record)
            out_of_contract_meta.append(
                {
                    "edge_type": "call",
                    "language": file_result.language,
                    "reason": reason,
                }
            )
    return (
        dedupe_edge_records(expected_filtered),
        dedupe_edge_records(full_truth),
        dedupe_edge_records(out_of_contract),
        out_of_contract_meta,
        diagnostics,
    )
