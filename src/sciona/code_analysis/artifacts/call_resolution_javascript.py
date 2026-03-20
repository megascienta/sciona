# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript-specific artifact call resolution rescue helpers."""

def resolve_javascript_structural_ambiguous(
    identifier,
    direct_candidates,
    fallback_candidates,
    caller_module,
    callable_qname_by_id,
    module_lookup,
    import_targets,
    expanded_import_targets,
    js_barrel_export_map,
    simple_identifier,
    module_in_scope,
    best_candidate_by_module_distance,
    allow_distance_fallback=True,
):
    candidates = list(dict.fromkeys(list(direct_candidates or fallback_candidates)))
    if not candidates:
        candidates = _infer_index_barrel_candidates(
            identifier=identifier,
            callable_qname_by_id=callable_qname_by_id,
            module_lookup=module_lookup,
            simple_identifier=simple_identifier,
        )

    if not candidates:
        return None

    local = [
        c for c in candidates
        if module_lookup.get(c) == caller_module
    ]

    if len(local) == 1:
        return local[0]
    
    scope = expanded_import_targets.get(caller_module, set())

    scoped = [
        c for c in candidates
        if module_lookup.get(c) in scope
    ]
    for barrel_target in js_barrel_export_map.get(caller_module, set()):
        for candidate in candidates:
            if module_lookup.get(candidate) == barrel_target and candidate not in scoped:
                scoped.append(candidate)
    if not scoped and ".index" in identifier.rsplit(".", 1)[0]:
        identifier_module = _collapse_index_module(identifier.rsplit(".", 1)[0])
        scoped = [
            candidate
            for candidate in candidates
            if (module_lookup.get(candidate) or "").startswith(f"{identifier_module}.")
        ]

    if len(scoped) == 1:
        return scoped[0]
    
    identifier_terminal = simple_identifier(identifier)

    if allow_distance_fallback and identifier_terminal:
        terminal_matches = [
            c
            for c in candidates
            if simple_identifier(callable_qname_by_id.get(c, "")) == identifier_terminal
        ]

        if len(terminal_matches) == 1:
            return terminal_matches[0]

    tail_matches = []
    if "." in identifier:
        tail_matches = [
            c
            for c in candidates
            if callable_qname_by_id.get(c, "").endswith(identifier)
        ]

    if len(tail_matches) == 1:
        return tail_matches[0]

    if not allow_distance_fallback:
        return None

    best = best_candidate_by_module_distance(
        candidates,
        caller_module=caller_module,
        module_lookup=module_lookup,
        callable_qname_by_id=callable_qname_by_id,
        import_targets=import_targets,
    )

    if best:
        return best

    return None


def build_javascript_barrel_export_map(
    *,
    import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    bounded_module_reachability,
) -> dict[str, set[str]]:
    barrel_modules = {
        module
        for module, file_path in module_file_by_name.items()
        if _is_javascript_index_module(file_path)
    }
    if not barrel_modules:
        return {}
    barrel_exports: dict[str, set[str]] = {}
    for barrel_module in sorted(barrel_modules):
        bindings = module_bindings_by_name.get(barrel_module, set())
        if not bindings:
            continue
        targets = bounded_module_reachability(import_targets, start=barrel_module, max_depth=4)
        exported_targets = {
            target
            for target in targets
            if bindings & module_bindings_by_name.get(target, set())
        }
        if exported_targets:
            barrel_exports[barrel_module] = exported_targets
    caller_map: dict[str, set[str]] = {}
    for caller_module, imported_modules in import_targets.items():
        for imported in imported_modules:
            exported = barrel_exports.get(imported, set())
            if not exported:
                continue
            caller_map.setdefault(caller_module, set()).update(exported)
    return caller_map


def _infer_index_barrel_candidates(
    *,
    identifier,
    callable_qname_by_id,
    module_lookup,
    simple_identifier,
):
    if ".index." not in identifier:
        return []
    terminal = simple_identifier(identifier)
    if not terminal:
        return []
    identifier_module = _collapse_index_module(identifier.rsplit(".", 1)[0])
    inferred = []
    for candidate, qname in callable_qname_by_id.items():
        if simple_identifier(qname) != terminal:
            continue
        module_name = module_lookup.get(candidate) or ""
        if module_name.startswith(f"{identifier_module}."):
            inferred.append(candidate)
    return inferred


def _collapse_index_module(module_name: str) -> str:
    collapsed = module_name.replace(".index.", ".")
    if collapsed.endswith(".index"):
        collapsed = collapsed[: -len(".index")]
    return collapsed


def _is_javascript_index_module(file_path: str) -> bool:
    normalized = str(file_path or "").replace("\\", "/")
    return (
        normalized.endswith("/index.js")
        or normalized.endswith("/index.mjs")
        or normalized.endswith("/index.cjs")
    )
