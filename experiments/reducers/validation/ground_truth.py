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
) -> Tuple[List[EdgeRecord], List[EdgeRecord], List[EdgeRecord], List[dict]]:
    # Contract-first truth: only in-repo, contract-compatible edges.
    expected_filtered: List[EdgeRecord] = []
    full_truth: List[EdgeRecord] = []
    out_of_contract: List[EdgeRecord] = []
    out_of_contract_meta: List[dict] = []
    standard_calls = standard_call_names(contract)

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
        )

    if entity.kind == "class":
        class_qname = entity.qualified_name
        matched_class = None
        for definition in file_result.defs:
            if definition.kind != "class":
                continue
            if definition.qualified_name == entity.qualified_name:
                matched_class = definition
                break
        entity_start = getattr(entity, "start_line", None)
        entity_end = getattr(entity, "end_line", None)
        if matched_class is None and entity_start and entity_end:
            containing = [
                definition
                for definition in file_result.defs
                if definition.kind == "class"
                and definition.start_line <= entity_start
                and definition.end_line >= entity_end
            ]
            if containing:
                containing.sort(key=lambda item: (item.end_line - item.start_line, item.qualified_name))
                matched_class = containing[0]
        if matched_class is None:
            leaf = entity.qualified_name.rsplit(".", 1)[-1]
            same_leaf = [
                definition
                for definition in file_result.defs
                if definition.kind == "class"
                and definition.qualified_name.rsplit(".", 1)[-1] == leaf
            ]
            if len(same_leaf) == 1:
                matched_class = same_leaf[0]
        if matched_class is not None:
            class_qname = matched_class.qualified_name
        prefix = f"{class_qname}."
        for definition in file_result.defs:
            if definition.kind != "method":
                continue
            if not definition.qualified_name.startswith(prefix):
                continue
            callee_qname = definition.qualified_name
            record = EdgeRecord(
                caller=entity.qualified_name,
                callee=callee_qname.split(".")[-1],
                callee_qname=callee_qname,
            )
            expected_filtered.append(record)
            full_truth.append(record)
        return (
            dedupe_edge_records(expected_filtered),
            dedupe_edge_records(full_truth),
            dedupe_edge_records(out_of_contract),
            out_of_contract_meta,
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
            out_of_contract.append(full_record)
            reason = classify_call_reason(
                edge=edge,
                language=file_result.language,
                call_resolution=call_resolution,
                contract=contract,
            )
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
    )
