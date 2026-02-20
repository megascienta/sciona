# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from typing import Dict, List, Tuple

from .call_contract import call_in_contract
from .import_contract import resolve_import_contract
from .independent.shared import EdgeRecord, FileParseResult
from .out_of_contract import classify_call_reason, classify_import_reason

_EXCLUDED_CALL_REASONS = {"external", "standard_call"}
_EXCLUDED_IMPORT_REASONS = {"external"}


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
) -> Tuple[List[EdgeRecord], List[EdgeRecord], List[dict]]:
    expected: List[EdgeRecord] = []
    out_of_contract: List[EdgeRecord] = []
    out_of_contract_meta: List[dict] = []

    if entity.kind == "module":
        for module_name, file_path, language, edge in module_imports_by_prefix.get(
            entity.qualified_name, []
        ):
            resolved = resolve_import_contract(
                edge.target_module,
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
                caller=module_name,
                callee=resolved or edge.target_module,
                callee_qname=resolved,
            )
            if edge.dynamic or not resolved:
                reason = classify_import_reason(
                    raw_target=edge.target_module,
                    resolved=resolved,
                    language=language,
                    repo_prefix=repo_prefix,
                )
                if reason not in _EXCLUDED_IMPORT_REASONS:
                    out_of_contract.append(record)
                    out_of_contract_meta.append(
                        {
                            "edge_type": "import",
                            "language": language,
                            "reason": reason,
                        }
                    )
            else:
                expected.append(record)
        if not module_imports_by_prefix.get(entity.qualified_name):
            for edge in normalized_imports:
                resolved = resolve_import_contract(
                    edge.target_module,
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
                    caller=file_result.module_qualified_name,
                    callee=resolved or edge.target_module,
                    callee_qname=resolved,
                )
                if edge.dynamic or not resolved:
                    reason = classify_import_reason(
                        raw_target=edge.target_module,
                        resolved=resolved,
                        language=file_result.language,
                        repo_prefix=repo_prefix,
                    )
                    if reason not in _EXCLUDED_IMPORT_REASONS:
                        out_of_contract.append(record)
                        out_of_contract_meta.append(
                            {
                                "edge_type": "import",
                                "language": file_result.language,
                                "reason": reason,
                            }
                        )
                else:
                    expected.append(record)
        return expected, out_of_contract, out_of_contract_meta

    if entity.kind == "class":
        prefix = f"{entity.qualified_name}."
        for edge in normalized_calls:
            if not edge.caller.startswith(prefix):
                continue
            record = EdgeRecord(edge.caller, edge.callee, edge.callee_qname)
            if edge.dynamic or not call_in_contract(
                edge, entity.module_qualified_name, call_resolution, contract
            ):
                reason = classify_call_reason(
                    edge=edge,
                    language=file_result.language,
                    call_resolution=call_resolution,
                    contract=contract,
                )
                if reason not in _EXCLUDED_CALL_REASONS:
                    out_of_contract.append(record)
                    out_of_contract_meta.append(
                        {
                            "edge_type": "call",
                            "language": file_result.language,
                            "reason": reason,
                        }
                    )
            else:
                expected.append(record)
        return expected, out_of_contract, out_of_contract_meta

    for edge in normalized_calls:
        if edge.caller != entity.qualified_name:
            continue
        record = EdgeRecord(edge.caller, edge.callee, edge.callee_qname)
        if edge.dynamic or not call_in_contract(
            edge, entity.module_qualified_name, call_resolution, contract
        ):
            reason = classify_call_reason(
                edge=edge,
                language=file_result.language,
                call_resolution=call_resolution,
                contract=contract,
            )
            if reason not in _EXCLUDED_CALL_REASONS:
                out_of_contract.append(record)
                out_of_contract_meta.append(
                    {
                        "edge_type": "call",
                        "language": file_result.language,
                        "reason": reason,
                    }
                )
        else:
            expected.append(record)
    return expected, out_of_contract, out_of_contract_meta
