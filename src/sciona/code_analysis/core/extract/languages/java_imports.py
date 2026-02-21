# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java import and package extraction utilities."""

from __future__ import annotations

from typing import Optional

from .....runtime import paths as runtime_paths
from ...normalize.model import FileSnapshot
from ..utils import find_nodes_of_type
from .shared import repo_root_from_snapshot


def extract_package(root, content: bytes) -> Optional[str]:
    for node in find_nodes_of_type(root, "package_declaration"):
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


def normalize_import(
    fragment: str,
    module_name: str,
    snapshot: FileSnapshot,
    *,
    module_prefix: str | None,
) -> Optional[str]:
    raw = fragment.strip()
    if not raw.startswith("import"):
        return None
    is_static = raw.startswith("import static")
    text = raw[len("import") :].strip()
    if text.startswith("static"):
        text = text[len("static") :].strip()
    if text.endswith(";"):
        text = text[:-1]
    text = text.strip()
    if text.endswith(".*"):
        return None
    if not text:
        return None
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


def import_simple_name(fragment: str) -> str | None:
    raw = fragment.strip()
    if not raw.startswith("import"):
        return None
    is_static = raw.startswith("import static")
    text = raw[len("import") :].strip()
    if text.startswith("static"):
        text = text[len("static") :].strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    if text.endswith(".*"):
        return None
    if is_static and "." in text:
        text = text.rsplit(".", 1)[0]
    if not text:
        return None
    return text.split(".")[-1]


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
