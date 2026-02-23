# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations


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


def _qualifier_from_text(edge) -> str | None:
    text = (getattr(edge, "callee_text", None) or "").strip()
    if not text:
        text = (edge.callee_qname or "").strip()
    if not text:
        return None
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    if "." not in text:
        return None
    return text.rsplit(".", 1)[0].strip() or None


def _candidate_identifiers(edge) -> list[str]:
    candidates: list[str] = []
    for raw in [edge.callee, edge.callee_qname]:
        if not raw:
            continue
        value = raw.strip()
        if not value:
            continue
        if "." in value:
            candidates.append(value.split(".")[-1])
        else:
            candidates.append(value)
    text = (getattr(edge, "callee_text", None) or "").strip()
    if text:
        head = text.split("(", 1)[0].strip()
        if head:
            candidates.append(head.split(".")[-1].strip())
    seen: set[str] = set()
    ordered: list[str] = []
    for name in candidates:
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _by_module(candidates: list[str], module_lookup: dict[str, str], module: str) -> list[str]:
    return [candidate for candidate in candidates if module_lookup.get(candidate) == module]


def _by_prefix(candidates: list[str], prefix: str) -> list[str]:
    return [candidate for candidate in candidates if candidate.startswith(prefix)]


def _qualifier_leaf(edge) -> str | None:
    qualifier = _qualifier_from_text(edge)
    if not qualifier:
        return None
    return qualifier.split(".")[-1]


def _qualifier_tokens(edge) -> list[str]:
    qualifier = _qualifier_from_text(edge)
    if not qualifier:
        return []
    return [token for token in qualifier.split(".") if token]


def resolve_call_in_contract(
    edge,
    caller_qname: str,
    caller_module: str,
    call_resolution: dict,
    contract: dict,
) -> str | None:
    require_in_repo = contract.get("call_contract", {}).get("require_callee_in_repo", True)
    if edge.callee_qname and require_in_repo:
        module_lookup: dict[str, str] = call_resolution.get("module_lookup", {})
        if edge.callee_qname in module_lookup:
            return edge.callee_qname
    identifiers = _candidate_identifiers(edge)
    if not identifiers:
        return None
    identifier = identifiers[0]
    if not require_in_repo:
        return edge.callee_qname or identifier

    symbol_index: dict[str, list[str]] = call_resolution.get("symbol_index", {})
    module_lookup: dict[str, str] = call_resolution.get("module_lookup", {})
    import_targets: dict[str, set[str]] = call_resolution.get("import_targets", {})
    class_name_index: dict[str, list[str]] = call_resolution.get("class_name_index", {})
    class_method_index: dict[str, dict[str, str]] = call_resolution.get("class_method_index", {})
    module_symbol_index: dict[str, dict[str, list[str]]] = call_resolution.get(
        "module_symbol_index", {}
    )
    import_symbol_hints: dict[str, dict[str, list[str]]] = call_resolution.get(
        "import_symbol_hints", {}
    )
    namespace_aliases: dict[str, dict[str, str]] = call_resolution.get("namespace_aliases", {})
    receiver_bindings: dict[str, dict[str, list[str]]] = call_resolution.get(
        "receiver_bindings", {}
    )

    class_qname = caller_qname.rsplit(".", 1)[0] if "." in caller_qname else ""
    class_methods = class_method_index.get(class_qname, {})
    local_method = class_methods.get(identifier)
    if local_method:
        return local_method

    qualifier_tokens = _qualifier_tokens(edge)
    if qualifier_tokens:
        scope_bindings = receiver_bindings.get(caller_qname, {})
        receiver_name = qualifier_tokens[-1]
        bound = scope_bindings.get(receiver_name, [])
        scoped = _by_prefix(candidates := (symbol_index.get(identifier) or []), f"{bound[0]}.") if len(bound) == 1 else []
        if len(scoped) == 1:
            return scoped[0]

    module_symbols = module_symbol_index.get(caller_module, {}).get(identifier, [])
    if len(module_symbols) == 1:
        return module_symbols[0]

    candidates = symbol_index.get(identifier) or []
    if not candidates and len(identifiers) > 1:
        for alternate in identifiers[1:]:
            candidates = symbol_index.get(alternate) or []
            if candidates:
                identifier = alternate
                break
    if len(candidates) == 1:
        return candidates[0]
    if not candidates or not caller_module:
        return None

    same_module = _by_module(candidates, module_lookup, caller_module)
    if len(same_module) == 1:
        return same_module[0]

    qualifier_leaf = _qualifier_leaf(edge)
    if qualifier_leaf:
        hinted = import_symbol_hints.get(caller_module, {}).get(qualifier_leaf, [])
        if len(hinted) == 1:
            return hinted[0]

        class_candidates = class_name_index.get(qualifier_leaf) or []
        if class_candidates:
            scoped = _by_prefix(candidates, f"{class_candidates[0]}.")
            if len(scoped) == 1:
                return scoped[0]

        namespace_target = namespace_aliases.get(caller_module, {}).get(qualifier_leaf)
        if namespace_target:
            module_symbols = module_symbol_index.get(namespace_target, {}).get(identifier, [])
            if len(module_symbols) == 1:
                return module_symbols[0]

    allowed_modules = set(import_targets.get(caller_module, set()))
    allowed_modules.add(caller_module)
    narrowed = [
        candidate for candidate in candidates if module_lookup.get(candidate) in allowed_modules
    ]
    hinted_direct = import_symbol_hints.get(caller_module, {}).get(identifier, [])
    hinted_narrowed = [candidate for candidate in hinted_direct if candidate in candidates]
    if len(hinted_narrowed) == 1:
        return hinted_narrowed[0]
    if len(narrowed) == 1:
        return narrowed[0]
    return None


def call_in_contract(
    edge,
    caller_qname: str,
    caller_module: str,
    call_resolution: dict,
    contract: dict,
) -> bool:
    return (
        resolve_call_in_contract(
            edge, caller_qname, caller_module, call_resolution, contract
        )
        is not None
    )
