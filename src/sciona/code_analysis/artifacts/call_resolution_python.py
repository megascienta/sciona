# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python-specific artifact call resolution rescue helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence


_CONSTRUCTOR_TERMINALS = {"__new__", "__init__", "new", "constructor"}


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
    if not caller_module:
        return None
    terminal = simple_identifier(identifier)
    if not terminal:
        return None
    if not candidates:
        candidates = _infer_package_surface_candidates(
            identifier=identifier,
            terminal=terminal,
            callable_qname_by_id=callable_qname_by_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_bindings_by_name=module_bindings_by_name,
            module_file_by_name=module_file_by_name,
            simple_identifier=simple_identifier,
            bounded_module_reachability=bounded_module_reachability,
        )
    if not candidates:
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
        if not _candidate_matches_terminal(
            terminal=terminal,
            candidate_qname=qname,
            simple_identifier=simple_identifier,
        ):
            continue
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
            if terminal in _CONSTRUCTOR_TERMINALS:
                owner = qname.rsplit(".", 1)[0] if "." in qname else ""
                owner_terminal = simple_identifier(owner) if owner else ""
                if owner_terminal:
                    bindings[module].add(owner_terminal)
    return dict(bindings)


def python_export_scope_modules(
    *,
    caller_module: str,
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    bounded_module_reachability,
) -> set[str]:
    seed_modules: set[str] = set()
    for module in {caller_module, *_module_ancestors(caller_module)}:
        seed_modules.update(expanded_import_targets.get(module, set()))
        seed_modules.update(import_targets.get(module, set()))
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


def _infer_package_surface_candidates(
    *,
    identifier: str,
    terminal: str,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    simple_identifier,
    bounded_module_reachability,
) -> list[str]:
    if "." not in identifier:
        return []
    identifier_module = identifier.rsplit(".", 1)[0]
    scope_modules: set[str] = set()
    module_parts = [part for part in identifier_module.split(".") if part]
    for end in range(1, len(module_parts) + 1):
        prefix = ".".join(module_parts[:end])
        scope_modules.add(prefix)
        scope_modules.update(import_targets.get(prefix, set()))
        scope_modules.update(expanded_import_targets.get(prefix, set()))
        file_path = module_file_by_name.get(prefix, "")
        if str(file_path).endswith("__init__.py"):
            scope_modules.update(
                bounded_module_reachability(import_targets, start=prefix, max_depth=4)
            )
    candidate_ids: list[str] = []
    for callable_id, qname in callable_qname_by_id.items():
        if not _candidate_matches_terminal(
            terminal=terminal,
            candidate_qname=qname,
            simple_identifier=simple_identifier,
        ):
            continue
        module = module_lookup.get(callable_id)
        if not module:
            continue
        if terminal not in module_bindings_by_name.get(module, set()):
            continue
        if module in scope_modules or module.startswith(f"{identifier_module}."):
            candidate_ids.append(callable_id)
    return list(dict.fromkeys(candidate_ids))


def _candidate_matches_terminal(
    *,
    terminal: str,
    candidate_qname: str,
    simple_identifier,
) -> bool:
    if not candidate_qname:
        return False
    candidate_terminal = simple_identifier(candidate_qname)
    if candidate_terminal == terminal:
        return True
    if candidate_terminal not in _CONSTRUCTOR_TERMINALS:
        return False
    owner = candidate_qname.rsplit(".", 1)[0] if "." in candidate_qname else ""
    return bool(owner and simple_identifier(owner) == terminal)


def _module_ancestors(module_name: str) -> set[str]:
    parts = [part for part in module_name.split(".") if part]
    if len(parts) < 2:
        return set()
    ancestors: set[str] = set()
    for end in range(len(parts) - 1, 0, -1):
        ancestors.add(".".join(parts[:end]))
    return ancestors
