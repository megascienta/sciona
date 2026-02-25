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
    text = import_name_from_node(node, content)
    if not text:
        return None
    is_static = is_static_import(node, content)
    if text.endswith(".*"):
        text = text[:-2]
    if is_static and "." in text:
        text = text.rsplit(".", 1)[0]
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
    text = import_name_from_node(node, content)
    if not text:
        return None
    if text.endswith(".*"):
        text = text[:-2]
    if is_static_import(node, content) and "." in text:
        text = text.rsplit(".", 1)[0]
    return text.split(".")[-1] if text else None


def import_name_from_node(node, content: bytes) -> str | None:
    if node is None:
        return None
    scoped = node.child_by_field_name("name")
    if scoped is None:
        scoped = node.child_by_field_name("path")
    if scoped is None:
        text = content[node.start_byte : node.end_byte].decode("utf-8").strip()
        if text.startswith("import"):
            text = text[len("import") :].strip()
            if text.startswith("static"):
                text = text[len("static") :].strip()
            if text.endswith(";"):
                text = text[:-1].strip()
            return text or None
        return None
    return content[scoped.start_byte : scoped.end_byte].decode("utf-8").strip()


def is_static_import(node, content: bytes) -> bool:
    text = content[node.start_byte : node.end_byte].decode("utf-8").strip()
    return text.startswith("import static")


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
