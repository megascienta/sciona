# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python-specific artifact call resolution rescue helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence


def resolve_python_export_chain_ambiguous(
    *,
    identifier: str,
    direct_candidates: Sequence[str],
    fallback_candidates: Sequence[str],
    caller_module: str | None,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    simple_identifier,
    module_in_scope,
    best_candidate_by_module_path,
    bounded_module_reachability,
) -> str | None:
    candidates = list(dict.fromkeys(list(direct_candidates) or list(fallback_candidates)))
    if len(candidates) < 2 or not caller_module:
        return None
    terminal = simple_identifier(identifier)
    if not terminal:
        return None
    allowed_modules = python_export_scope_modules(
        caller_module=caller_module,
        import_targets=import_targets,
        expanded_import_targets=expanded_import_targets,
        module_file_by_name=module_file_by_name,
        bounded_module_reachability=bounded_module_reachability,
    )
    allowed_modules.add(caller_module)
    in_scope = []
    for candidate in candidates:
        module = module_lookup.get(candidate)
        if not module:
            continue
        if not module_in_scope(module, allowed_modules, allow_descendants=False):
            continue
        qname = callable_qname_by_id.get(candidate, "")
        if qname and simple_identifier(qname) == terminal:
            if terminal not in module_bindings_by_name.get(module, set()):
                continue
            in_scope.append(candidate)
    if not in_scope:
        return None
    return best_candidate_by_module_path(in_scope, module_lookup, callable_qname_by_id)


def build_module_binding_index(
    *,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    simple_identifier,
) -> dict[str, set[str]]:
    bindings: dict[str, set[str]] = defaultdict(set)
    for callable_id, qname in callable_qname_by_id.items():
        module = module_lookup.get(callable_id)
        if not module:
            continue
        terminal = simple_identifier(qname)
        if terminal:
            bindings[module].add(terminal)
    return dict(bindings)


def python_export_scope_modules(
    *,
    caller_module: str,
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    bounded_module_reachability,
) -> set[str]:
    seed_modules = set(expanded_import_targets.get(caller_module, set()))
    seed_modules.update(import_targets.get(caller_module, set()))
    init_roots = {
        module
        for module in seed_modules
        if str(module_file_by_name.get(module, "")).endswith("__init__.py")
    }
    if not init_roots:
        init_roots = seed_modules
    scoped: set[str] = set(seed_modules)
    for root in init_roots:
        scoped.update(bounded_module_reachability(import_targets, start=root, max_depth=4))
    return scoped
