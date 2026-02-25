# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python import extraction utilities."""

from __future__ import annotations

import importlib.util
from typing import List, Optional

from .....runtime import packaging as runtime_packaging
from .....runtime import paths as runtime_paths
from ...normalize.model import FileSnapshot
from ..utils import find_nodes_of_types_query
from .import_model import NormalizedImportModel
from .query_surface import PYTHON_IMPORT_NODE_TYPES
from .shared import is_internal_module, repo_root_from_snapshot


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
    for child in find_nodes_of_types_query(
        root,
        language_name="python",
        node_types=PYTHON_IMPORT_NODE_TYPES,
    ):
        model.imports_seen += 1
        if not _is_direct_child(child, root):
            continue
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
                if not normalized or not is_internal_module(normalized, module_index):
                    continue
                model.modules.append(normalized)
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
            if not normalized or not is_internal_module(normalized, module_index):
                continue
            model.modules.append(normalized)
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
            module = content[child.start_byte : child.end_byte].decode("utf-8").strip()
            if module:
                extracted.append((module, None))
        elif child.type == "aliased_import":
            name_node = child.child_by_field_name("name")
            alias_node = child.child_by_field_name("alias")
            if name_node is None:
                continue
            module = content[name_node.start_byte : name_node.end_byte].decode("utf-8").strip()
            alias = (
                content[alias_node.start_byte : alias_node.end_byte].decode("utf-8").strip()
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
        elif child.type == "identifier":
            name = content[child.start_byte : child.end_byte].decode("utf-8").strip()
            if name not in {"from", "import"}:
                names.append((name, None))
        elif child.type == "aliased_import":
            name_node = child.child_by_field_name("name")
            alias_node = child.child_by_field_name("alias")
            if name_node is None:
                continue
            name = content[name_node.start_byte : name_node.end_byte].decode("utf-8").strip()
            alias = (
                content[alias_node.start_byte : alias_node.end_byte].decode("utf-8").strip()
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
        value = content[module_node.start_byte : module_node.end_byte].decode("utf-8").strip()
        return value or None
    # `from . import x` and `from ..pkg import x` are represented as relative_import.
    relative_node = next(
        (child for child in getattr(node, "children", []) if child.type == "relative_import"),
        None,
    )
    if relative_node is None:
        return None
    value = content[relative_node.start_byte : relative_node.end_byte].decode("utf-8").strip()
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
        try:
            resolved = importlib.util.resolve_name(target, package)
            return resolved
        except ImportError:
            return None
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


def _is_direct_child(node, root) -> bool:
    parent = getattr(node, "parent", None)
    if parent is None:
        return False
    return (
        parent.start_byte == root.start_byte
        and parent.end_byte == root.end_byte
        and parent.type == root.type
    )
