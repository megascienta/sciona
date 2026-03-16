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
    simple_identifier,
    module_in_scope,
    best_candidate_by_module_distance,
):
    candidates = list(direct_candidates or fallback_candidates)

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

    if len(scoped) == 1:
        return scoped[0]
    
    identifier_terminal = simple_identifier(identifier)

    terminal_matches = [
        c
        for c in candidates
        if simple_identifier(callable_qname_by_id.get(c, "")) == identifier_terminal
    ]

    if len(terminal_matches) == 1:
        return terminal_matches[0]

    tail_matches = [
        c
        for c in candidates
        if callable_qname_by_id.get(c, "").endswith(identifier)
    ]

    if len(tail_matches) == 1:
        return tail_matches[0]

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