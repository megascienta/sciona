# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from . import config
from .import_contract import resolve_import_contract
from .independent.shared import FileParseResult


def build_independent_call_resolution(
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]],
    module_names: set[str],
    repo_root: Path,
    repo_prefix: str,
    local_packages: set[str],
    all_nodes: List[dict] | None = None,
) -> dict:
    symbol_index: Dict[str, set[str]] = {}
    module_lookup: Dict[str, str] = {}
    import_targets: Dict[str, set[str]] = {}

    for entry in all_nodes or []:
        node_type = entry.get("node_type") or entry.get("node_kind")
        qname = entry.get("qualified_name")
        if node_type not in {"function", "method"} or not isinstance(qname, str) or not qname:
            continue
        identifier = qname.split(".")[-1]
        symbol_index.setdefault(identifier, set()).add(qname)
        module_name = entry.get("module_qualified_name")
        if not module_name:
            parts = qname.split(".")
            module_name = ".".join(parts[:-1]) if len(parts) > 1 else qname
        module_lookup[qname] = module_name

    for file_result in independent_results.values():
        module_name = file_result.module_qualified_name
        for definition in file_result.defs:
            if definition.kind not in {"function", "method"}:
                continue
            qname = definition.qualified_name
            identifier = qname.split(".")[-1]
            symbol_index.setdefault(identifier, set()).add(qname)
            module_lookup[qname] = module_name

        _, normalized_imports = normalized_edge_map.get(file_result.file_path, ([], []))
        for edge in normalized_imports:
            resolved = resolve_import_contract(
                edge.target_module,
                file_result.file_path,
                module_name,
                file_result.language,
                module_names,
                repo_root,
                repo_prefix,
                local_packages,
            )
            if resolved:
                import_targets.setdefault(module_name, set()).add(resolved)

    return {
        "mode": config.STRICT_CONTRACT_MODE,
        "symbol_index": {key: sorted(values) for key, values in symbol_index.items()},
        "module_lookup": module_lookup,
        "import_targets": import_targets,
    }


__all__ = ["build_independent_call_resolution"]
