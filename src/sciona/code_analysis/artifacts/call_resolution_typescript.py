# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript-specific artifact call resolution rescue helpers."""

from __future__ import annotations

from typing import Sequence


def resolve_typescript_barrel_ambiguous(
    *,
    identifier: str,
    direct_candidates: Sequence[str],
    fallback_candidates: Sequence[str],
    caller_module: str | None,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    ts_barrel_export_map: dict[str, set[str]],
    simple_identifier,
    module_in_scope,
    best_candidate_by_module_distance,
) -> str | None:
    candidates = list(dict.fromkeys(list(direct_candidates) or list(fallback_candidates)))
    if len(candidates) < 2 or not caller_module:
        return None
    allowed_modules = set(expanded_import_targets.get(caller_module, set()))
    allowed_modules.update(import_targets.get(caller_module, set()))
    allowed_modules.add(caller_module)
    in_scope = []
    for candidate in candidates:
        module = module_lookup.get(candidate)
        if not module:
            continue
        if module_in_scope(module, allowed_modules, allow_descendants=True):
            in_scope.append(candidate)
    for barrel_target in ts_barrel_export_map.get(caller_module, set()):
        for candidate in candidates:
            if module_lookup.get(candidate) == barrel_target and candidate not in in_scope:
                in_scope.append(candidate)
    if not in_scope:
        return None
    exact_qname = [c for c in in_scope if callable_qname_by_id.get(c) == identifier]
    if len(exact_qname) == 1:
        return exact_qname[0]
    if len(exact_qname) > 1:
        in_scope = exact_qname
    terminal = simple_identifier(identifier)
    if terminal:
        terminal_matches = [
            c for c in in_scope if simple_identifier(callable_qname_by_id.get(c, "")) == terminal
        ]
        if terminal_matches:
            in_scope = terminal_matches
    return best_candidate_by_module_distance(
        in_scope,
        caller_module=caller_module,
        module_lookup=module_lookup,
        callable_qname_by_id=callable_qname_by_id,
        import_targets=import_targets,
    )


def build_typescript_barrel_export_map(
    *,
    import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    bounded_module_reachability,
) -> dict[str, set[str]]:
    barrel_map: dict[str, set[str]] = {}
    for module, file_path in module_file_by_name.items():
        normalized = file_path.replace("\\", "/")
        if not normalized.endswith("/index.ts") and not normalized.endswith("/index.tsx"):
            continue
        targets = bounded_module_reachability(import_targets, start=module, max_depth=4)
        exported: set[str] = set()
        bindings = module_bindings_by_name.get(module, set())
        for target in targets:
            if bindings & module_bindings_by_name.get(target, set()):
                exported.add(target)
        if exported:
            barrel_map[module] = exported
    return barrel_map
