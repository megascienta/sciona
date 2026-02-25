# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java import and package extraction utilities."""

from __future__ import annotations

from typing import Optional

from .....runtime import paths as runtime_paths
from ...normalize.model import FileSnapshot
from ..utils import find_nodes_of_types_query
from .query_surface import JAVA_PACKAGE_NODE_TYPES
from .shared import repo_root_from_snapshot


def extract_package(root, content: bytes) -> Optional[str]:
    for node in find_nodes_of_types_query(
        root,
        language_name="java",
        node_types=JAVA_PACKAGE_NODE_TYPES,
    ):
        fragment = content[node.start_byte : node.end_byte].decode("utf-8").strip()
        if not fragment.startswith("package"):
            continue
        fragment = fragment[len("package") :].strip()
        if fragment.endswith(";"):
            fragment = fragment[:-1].strip()
        return fragment or None
    return None


def module_prefix_for_package(module_name: str, package_name: Optional[str]) -> str | None:
    if not package_name:
        return None
    module_parts = module_name.split(".")
    package_parts = package_name.split(".")
    if len(module_parts) < len(package_parts):
        return None
    for idx in range(len(module_parts) - len(package_parts), -1, -1):
        if module_parts[idx : idx + len(package_parts)] == package_parts:
            prefix_parts = module_parts[:idx]
            return ".".join(prefix_parts) if prefix_parts else None
    return None


def normalize_import_node(
    node,
    content: bytes,
    module_name: str,
    snapshot: FileSnapshot,
    *,
    module_prefix: str | None,
) -> Optional[str]:
    parts = import_name_parts(node, content)
    if not parts:
        return None
    target_parts = parts[:-1] if is_static_import(node) and len(parts) > 1 else parts
    text = ".".join(target_parts)
    if not text:
        return None
    repo_root = repo_root_from_snapshot(snapshot)
    repo_prefix = runtime_paths.repo_name_prefix(repo_root)
    if repo_prefix and (text == repo_prefix or text.startswith(f"{repo_prefix}.")):
        return text
    top_package = top_level_package(module_name, repo_prefix)
    if top_package and (text == top_package or text.startswith(f"{top_package}.")):
        return f"{repo_prefix}.{text}" if repo_prefix else text
    if module_prefix:
        return f"{module_prefix}.{text}"
    return text


def import_simple_name_node(node, content: bytes) -> str | None:
    parts = import_name_parts(node, content)
    if not parts:
        return None
    target_parts = parts[:-1] if is_static_import(node) and len(parts) > 1 else parts
    return target_parts[-1] if target_parts else None


def import_name_from_node(node, content: bytes) -> str | None:
    parts = import_name_parts(node, content)
    if not parts:
        return None
    return ".".join(parts)


def is_static_import(node) -> bool:
    return any(child.type == "static" for child in getattr(node, "children", []))


def import_name_parts(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    scoped = node.child_by_field_name("name")
    if scoped is None:
        scoped = node.child_by_field_name("path")
    if scoped is None:
        scoped = next(
            (child for child in getattr(node, "children", []) if child.type == "scoped_identifier"),
            None,
        )
    if scoped is None:
        return ()
    return scoped_identifier_parts(scoped, content)


def scoped_identifier_parts(node, content: bytes) -> tuple[str, ...]:
    if node is None:
        return ()
    if node.type == "identifier":
        value = content[node.start_byte : node.end_byte].decode("utf-8").strip()
        return (value,) if value else ()
    if node.type != "scoped_identifier":
        return ()
    scope_node = node.child_by_field_name("scope")
    name_node = node.child_by_field_name("name")
    head = scoped_identifier_parts(scope_node, content) if scope_node is not None else ()
    tail = scoped_identifier_parts(name_node, content) if name_node is not None else ()
    return (*head, *tail)


def top_level_package(module_name: str, repo_prefix: str) -> str | None:
    if repo_prefix and (
        module_name == repo_prefix or module_name.startswith(f"{repo_prefix}.")
    ):
        remainder = module_name[len(repo_prefix) + 1 :]
    else:
        remainder = module_name
    if not remainder:
        return None
    return remainder.split(".", 1)[0]
