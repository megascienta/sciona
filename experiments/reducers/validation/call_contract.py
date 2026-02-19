# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations


def build_call_resolution_context(module_overviews: dict[str, dict]) -> dict:
    symbol_index: dict[str, set[str]] = {}
    module_lookup: dict[str, str] = {}
    for module_name, overview in module_overviews.items():
        for entry in (overview.get("functions", []) or []):
            qname = entry.get("qualified_name")
            if not qname:
                continue
            identifier = qname.split(".")[-1]
            symbol_index.setdefault(identifier, set()).add(qname)
            module_lookup[qname] = module_name
        for entry in (overview.get("methods", []) or []):
            qname = entry.get("qualified_name")
            if not qname:
                continue
            identifier = qname.split(".")[-1]
            symbol_index.setdefault(identifier, set()).add(qname)
            module_lookup[qname] = module_name
    return {
        "symbol_index": {k: sorted(v) for k, v in symbol_index.items()},
        "module_lookup": module_lookup,
    }


def build_call_resolution_context_from_nodes(nodes: list[dict]) -> dict:
    symbol_index: dict[str, set[str]] = {}
    module_lookup: dict[str, str] = {}
    for entry in nodes:
        node_type = entry.get("node_type") or entry.get("node_kind")
        if node_type not in {"function", "method"}:
            continue
        qname = entry.get("qualified_name")
        if not qname:
            continue
        identifier = qname.split(".")[-1]
        symbol_index.setdefault(identifier, set()).add(qname)
        module_name = entry.get("module_qualified_name")
        if not module_name:
            parts = qname.split(".")
            module_name = ".".join(parts[:-1]) if len(parts) > 1 else qname
        module_lookup[qname] = module_name
    return {
        "symbol_index": {k: sorted(v) for k, v in symbol_index.items()},
        "module_lookup": module_lookup,
    }


def call_in_contract(
    edge,
    caller_module: str,
    call_resolution: dict,
    contract: dict,
) -> bool:
    require_in_repo = (
        contract.get("call_contract", {}).get("require_callee_in_repo", True)
    )
    identifier = (edge.callee or "").strip()
    if not identifier and edge.callee_qname:
        identifier = edge.callee_qname.split(".")[-1]
    if not identifier:
        return False
    if not require_in_repo:
        return True

    symbol_index: dict[str, list[str]] = call_resolution.get("symbol_index", {})
    module_lookup: dict[str, str] = call_resolution.get("module_lookup", {})
    import_targets: dict[str, set[str]] = call_resolution.get("import_targets", {})

    candidates = symbol_index.get(identifier) or []
    if len(candidates) == 1:
        return True if require_in_repo else True
    if not candidates or not caller_module:
        return False
    allowed_modules = set(import_targets.get(caller_module, set()))
    allowed_modules.add(caller_module)
    narrowed = [
        candidate for candidate in candidates if module_lookup.get(candidate) in allowed_modules
    ]
    if len(narrowed) == 1:
        return True if require_in_repo else True
    return False
