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
    class_name_index: Dict[str, set[str]] = {}
    class_method_index: Dict[str, Dict[str, str]] = {}
    module_symbol_index: Dict[str, Dict[str, set[str]]] = {}
    import_symbol_hints: Dict[str, Dict[str, set[str]]] = {}
    namespace_aliases: Dict[str, Dict[str, str]] = {}
    receiver_bindings: Dict[str, Dict[str, set[str]]] = {}

    for entry in all_nodes or []:
        node_type = entry.get("node_type") or entry.get("node_kind")
        qname = entry.get("qualified_name")
        if not isinstance(qname, str) or not qname:
            continue
        if node_type == "class":
            class_name_index.setdefault(qname.split(".")[-1], set()).add(qname)
            continue
        if node_type not in {"function", "method"}:
            continue
        identifier = qname.split(".")[-1]
        symbol_index.setdefault(identifier, set()).add(qname)
        module_name = entry.get("module_qualified_name")
        if not module_name:
            parts = qname.split(".")
            module_name = ".".join(parts[:-1]) if len(parts) > 1 else qname
        module_lookup[qname] = module_name
        module_symbol_index.setdefault(module_name, {}).setdefault(identifier, set()).add(qname)
        class_scope = qname.rsplit(".", 1)[0] if "." in qname else ""
        if class_scope:
            class_method_index.setdefault(class_scope, {})[identifier] = qname

    def _register_receiver(scope: str, receiver: str, target_qname: str) -> None:
        if not scope or not receiver or not target_qname:
            return
        receiver_bindings.setdefault(scope, {}).setdefault(receiver, set()).add(target_qname)
        leaf = receiver.rsplit(".", 1)[-1].strip()
        if leaf and leaf != receiver:
            receiver_bindings.setdefault(scope, {}).setdefault(leaf, set()).add(target_qname)

    def _resolve_assignment_target(scope_module: str, value_text: str) -> list[str]:
        raw = (value_text or "").strip()
        if not raw:
            return []
        terminal = raw.split(".")[-1]
        candidates: set[str] = set()
        for qname in symbol_index.get(terminal, set()):
            candidates.add(qname)
        for qname in class_name_index.get(terminal, set()):
            candidates.add(qname)
        module_local = module_symbol_index.get(scope_module, {}).get(terminal, set())
        candidates.update(module_local)
        hinted = import_symbol_hints.get(scope_module, {}).get(terminal, set())
        candidates.update(hinted)
        qualifier = raw.split(".", 1)[0] if "." in raw else None
        if qualifier:
            alias_module = namespace_aliases.get(scope_module, {}).get(qualifier)
            if alias_module:
                mod_candidates = module_symbol_index.get(alias_module, {}).get(terminal, set())
                candidates.update(mod_candidates)
        return sorted(candidates)

    for file_result in independent_results.values():
        module_name = file_result.module_qualified_name
        class_methods: Dict[str, set[str]] = {}
        for definition in file_result.defs:
            if definition.kind == "class":
                class_name_index.setdefault(definition.qualified_name.split(".")[-1], set()).add(
                    definition.qualified_name
                )
                continue
            if definition.kind not in {"function", "method"}:
                continue
            qname = definition.qualified_name
            identifier = qname.split(".")[-1]
            symbol_index.setdefault(identifier, set()).add(qname)
            module_lookup[qname] = module_name
            module_symbol_index.setdefault(module_name, {}).setdefault(identifier, set()).add(qname)
            class_scope = qname.rsplit(".", 1)[0] if "." in qname else ""
            if class_scope:
                class_method_index.setdefault(class_scope, {})[identifier] = qname
                class_methods.setdefault(class_scope, set()).add(qname)

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
        for raw_import in file_result.import_edges:
            resolved = resolve_import_contract(
                raw_import.target_module,
                file_result.file_path,
                module_name,
                file_result.language,
                module_names,
                repo_root,
                repo_prefix,
                local_packages,
            )
            if not resolved:
                continue
            hint = (raw_import.target_text or "").strip()
            if not hint:
                continue
            if file_result.language == "python" and hint.startswith("from ") and " import " in hint:
                _, rest = hint.split("from ", 1)
                _, import_part = rest.split(" import ", 1)
                symbol_part = import_part.strip()
                if symbol_part == "*":
                    continue
                imported = symbol_part
                local_name = symbol_part
                if " as " in symbol_part:
                    imported, local_name = [part.strip() for part in symbol_part.split(" as ", 1)]
                candidate = f"{resolved}.{imported}" if imported else resolved
                if local_name:
                    import_symbol_hints.setdefault(module_name, {}).setdefault(
                        local_name, set()
                    ).add(candidate)
                continue
            if file_result.language == "python" and " as " in hint and not hint.startswith("from "):
                imported, local_name = [part.strip() for part in hint.split(" as ", 1)]
                if imported and local_name:
                    namespace_aliases.setdefault(module_name, {})[local_name] = (
                        f"{repo_prefix}.{imported}"
                        if repo_prefix and not imported.startswith(f"{repo_prefix}.")
                        else imported
                    )
                continue
            if file_result.language == "typescript":
                for token in hint.split(","):
                    token = token.strip()
                    if token.startswith("named:") and "->" in token:
                        src, local = token[len("named:") :].split("->", 1)
                        src = src.strip()
                        local = local.strip()
                        if src and local:
                            import_symbol_hints.setdefault(module_name, {}).setdefault(
                                local, set()
                            ).add(f"{resolved}.{src}")
                    elif token.startswith("default:"):
                        local = token[len("default:") :].strip()
                        if local:
                            import_symbol_hints.setdefault(module_name, {}).setdefault(
                                local, set()
                            ).add(f"{resolved}.{local}")
                    elif token.startswith("namespace:"):
                        local = token[len("namespace:") :].strip()
                        if local:
                            namespace_aliases.setdefault(module_name, {})[local] = resolved

        for assignment in file_result.assignment_hints:
            resolved_targets = _resolve_assignment_target(module_name, assignment.value_text)
            for target in resolved_targets:
                _register_receiver(assignment.scope, assignment.receiver, target)
            if assignment.scope.endswith(".constructor"):
                # Propagate constructor receiver bindings to sibling methods only when
                # target resolution is unique; ambiguous propagation creates false positives.
                if len(resolved_targets) != 1:
                    continue
                class_scope = assignment.scope.rsplit(".", 1)[0]
                for method_scope in sorted(class_methods.get(class_scope, set())):
                    if method_scope.endswith(".constructor"):
                        continue
                    _register_receiver(method_scope, assignment.receiver, resolved_targets[0])

    return {
        "mode": config.STRICT_CONTRACT_MODE,
        "symbol_index": {key: sorted(values) for key, values in symbol_index.items()},
        "module_lookup": module_lookup,
        "import_targets": import_targets,
        "class_name_index": {key: sorted(values) for key, values in class_name_index.items()},
        "class_method_index": class_method_index,
        "module_symbol_index": {
            module: {name: sorted(values) for name, values in by_name.items()}
            for module, by_name in module_symbol_index.items()
        },
        "import_symbol_hints": {
            module: {name: sorted(values) for name, values in by_name.items()}
            for module, by_name in import_symbol_hints.items()
        },
        "namespace_aliases": namespace_aliases,
        "receiver_bindings": {
            scope: {receiver: sorted(values) for receiver, values in by_receiver.items()}
            for scope, by_receiver in receiver_bindings.items()
        },
    }


__all__ = ["build_independent_call_resolution"]
