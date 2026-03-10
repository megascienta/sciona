# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python import extraction utilities."""

from __future__ import annotations

from typing import List, Optional

from .....runtime import packaging as runtime_packaging
from .....runtime import paths as runtime_paths
from ....core.normalize_model import FileSnapshot
from ....core.extract.parsing.query_helpers import find_direct_children_query
from ...common.import_model import NormalizedImportModel
from ...common.query_surface import PYTHON_IMPORT_NODE_TYPES
from ...common.shared import is_internal_module, node_text, repo_root_from_snapshot


def collect_python_imports(
    root,
    snapshot: FileSnapshot,
    module_name: str,
    *,
    module_index: set[str] | None,
) -> tuple[list[str], dict[str, str], dict[str, str], dict[str, str]]:
    model = collect_python_import_model(
        root,
        snapshot,
        module_name,
        module_index=module_index,
    )
    return (
        model.modules,
        model.import_aliases,
        model.member_aliases,
        model.raw_module_map,
    )


def collect_python_import_model(
    root,
    snapshot: FileSnapshot,
    module_name: str,
    *,
    module_index: set[str] | None,
) -> NormalizedImportModel:
    repo_root = repo_root_from_snapshot(snapshot)
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    local_packages = set(runtime_packaging.local_package_names(repo_root))
    model = NormalizedImportModel()
    is_package = snapshot.record.path.name == "__init__.py"

    def _append_module(module_qname: str) -> None:
        if module_qname and module_qname not in model.modules:
            model.modules.append(module_qname)

    for child in find_direct_children_query(root, language_name="python"):
        if child.type not in PYTHON_IMPORT_NODE_TYPES:
            continue
        model.imports_seen += 1
        if child.type == "import_statement":
            extracted = extract_import_statement_from_node(child, snapshot.content)
            for module, alias in extracted:
                normalized = normalize_import(
                    module,
                    module_name,
                    is_package,
                    repo_prefix=repo_prefix,
                    local_packages=local_packages,
                )
                if not normalized:
                    continue
                if not is_internal_module(normalized, module_index):
                    if module_index is not None:
                        model.imports_filtered_not_internal += 1
                    continue
                model.imports_internal += 1
                _append_module(normalized)
                model.raw_module_map[module] = normalized
                if alias:
                    model.import_aliases[alias] = normalized
                elif "." not in module:
                    model.import_aliases[module] = normalized
        elif child.type == "import_from_statement":
            module, names = extract_from_import_from_node(child, snapshot.content)
            if not module:
                continue
            normalized = normalize_import(
                module,
                module_name,
                is_package,
                repo_prefix=repo_prefix,
                local_packages=local_packages,
            )
            if not normalized:
                continue
            if not is_internal_module(normalized, module_index):
                if module_index is not None:
                    model.imports_filtered_not_internal += 1
                continue
            model.imports_internal += 1
            is_bare_relative = module.startswith(".") and not module.strip(".")
            resolved_submodules: list[str] = []
            for name, _alias in names:
                if name == "*":
                    continue
                candidate_module = f"{normalized}.{name}"
                if is_internal_module(candidate_module, module_index):
                    resolved_submodules.append(candidate_module)
            if resolved_submodules:
                if not is_bare_relative:
                    _append_module(normalized)
                for candidate_module in resolved_submodules:
                    _append_module(candidate_module)
            else:
                _append_module(normalized)
            model.raw_module_map[module] = normalized
            for name, alias in names:
                if name == "*":
                    continue
                model.member_aliases[alias or name] = f"{normalized}.{name}"
    return model


def extract_import_statement_from_node(
    node,
    content: bytes,
) -> List[tuple[str, str | None]]:
    extracted: list[tuple[str, str | None]] = []
    for child in getattr(node, "children", []):
        if child.type == "dotted_name":
            module = (node_text(child, content) or "").strip()
            if module:
                extracted.append((module, None))
        elif child.type == "aliased_import":
            name_node = child.child_by_field_name("name")
            alias_node = child.child_by_field_name("alias")
            if name_node is None:
                continue
            module = (node_text(name_node, content) or "").strip()
            alias = (
                (node_text(alias_node, content) or "").strip()
                if alias_node is not None
                else None
            )
            if module:
                extracted.append((module, alias or None))
    return extracted


def extract_from_import_from_node(
    node,
    content: bytes,
) -> tuple[str | None, List[tuple[str, str | None]]]:
    module = _module_from_import_from_node(node, content)
    names: list[tuple[str, str | None]] = []
    for child in getattr(node, "children", []):
        if child.type == "wildcard_import":
            names.append(("*", None))
        elif child.type == "dotted_name":
            name = (node_text(child, content) or "").strip()
            if name:
                names.append((name, None))
        elif child.type == "identifier":
            name = (node_text(child, content) or "").strip()
            if name not in {"from", "import"}:
                names.append((name, None))
        elif child.type == "aliased_import":
            name_node = child.child_by_field_name("name")
            alias_node = child.child_by_field_name("alias")
            if name_node is None:
                continue
            name = (node_text(name_node, content) or "").strip()
            alias = (
                (node_text(alias_node, content) or "").strip()
                if alias_node is not None
                else None
            )
            if name:
                names.append((name, alias or None))
    return module or None, names


def _module_from_import_from_node(node, content: bytes) -> str | None:
    module_node = node.child_by_field_name("module_name")
    if module_node is None:
        module_node = node.child_by_field_name("module")
    if module_node is not None:
        value = (node_text(module_node, content) or "").strip()
        return value or None
    # `from . import x` and `from ..pkg import x` are represented as relative_import.
    relative_node = next(
        (child for child in getattr(node, "children", []) if child.type == "relative_import"),
        None,
    )
    if relative_node is None:
        return None
    value = (node_text(relative_node, content) or "").strip()
    return value or None


def normalize_import(
    target: str,
    module_name: str,
    is_package: bool,
    *,
    repo_prefix: str,
    local_packages: set[str],
) -> Optional[str]:
    target = target.strip()
    if not target:
        return None
    if target.startswith("."):
        package = package_context(module_name, is_package)
        if not package:
            return None
        return _resolve_relative_import_syntax(target, package)
    if repo_prefix and (target == repo_prefix or target.startswith(f"{repo_prefix}.")):
        return target
    for package in local_packages:
        if target == package or target.startswith(f"{package}."):
            return f"{repo_prefix}.{target}" if repo_prefix else target
    return target


def package_context(module_name: str, is_package: bool) -> Optional[str]:
    if not module_name:
        return None
    if is_package:
        return module_name
    if "." in module_name:
        return module_name.rsplit(".", 1)[0]
    return None


def _resolve_relative_import_syntax(target: str, package: str) -> str | None:
    level = 0
    for ch in target:
        if ch == ".":
            level += 1
        else:
            break
    suffix = target[level:]
    package_parts = [part for part in package.split(".") if part]
    # Leading single-dot imports do not ascend; two dots ascend by one, etc.
    ascend = max(level - 1, 0)
    if ascend > len(package_parts) - 1:
        return None
    base_parts = package_parts[: len(package_parts) - ascend]
    if suffix:
        suffix_parts = [part for part in suffix.split(".") if part]
        if not suffix_parts:
            return None
        base_parts.extend(suffix_parts)
    if not base_parts:
        return None
    return ".".join(base_parts)
