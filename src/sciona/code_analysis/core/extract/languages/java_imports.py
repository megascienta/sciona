# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java import and package extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .....runtime import paths as runtime_paths
from ...normalize.model import FileSnapshot
from ..query_helpers import find_nodes_of_types_query
from .import_model import NormalizedImportModel
from .query_surface import JAVA_IMPORT_NODE_TYPES, JAVA_PACKAGE_NODE_TYPES
from .shared import is_internal_module, repo_root_from_snapshot


@dataclass(frozen=True)
class JavaImportBindings:
    normalized_module: str
    import_aliases: tuple[tuple[str, str], ...] = ()
    member_aliases: tuple[tuple[str, str], ...] = ()
    static_wildcard_targets: tuple[str, ...] = ()


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
    target_parts = (
        parts[:-1]
        if is_static_import(node) and not is_wildcard_import(node, content) and len(parts) > 1
        else parts
    )
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


def collect_java_import_bindings(
    node,
    content: bytes,
    module_name: str,
    snapshot: FileSnapshot,
    *,
    module_prefix: str | None,
) -> JavaImportBindings | None:
    normalized = normalize_import_node(
        node,
        content,
        module_name,
        snapshot,
        module_prefix=module_prefix,
    )
    if not normalized:
        return None
    parts = import_name_parts(node, content)
    if not parts:
        return JavaImportBindings(normalized_module=normalized)

    if is_static_import(node):
        if is_wildcard_import(node, content):
            return JavaImportBindings(
                normalized_module=normalized,
                static_wildcard_targets=(normalized,),
            )
        member_name = parts[-1]
        if not member_name:
            return JavaImportBindings(normalized_module=normalized)
        return JavaImportBindings(
            normalized_module=normalized,
            member_aliases=((member_name, f"{normalized}.{member_name}"),),
        )

    simple_name = parts[-1]
    if not simple_name:
        return JavaImportBindings(normalized_module=normalized)
    return JavaImportBindings(
        normalized_module=normalized,
        import_aliases=((simple_name, normalized),),
    )


def collect_java_import_model(
    root,
    content: bytes,
    module_name: str,
    snapshot: FileSnapshot,
    *,
    module_prefix: str | None,
    module_index: set[str] | None,
) -> NormalizedImportModel:
    model = NormalizedImportModel()
    for import_node in find_nodes_of_types_query(
        root,
        language_name="java",
        node_types=JAVA_IMPORT_NODE_TYPES,
    ):
        model.imports_seen += 1
        bindings = collect_java_import_bindings(
            import_node,
            content,
            module_name,
            snapshot,
            module_prefix=module_prefix,
        )
        if bindings is None:
            continue
        normalized = bindings.normalized_module
        if not is_internal_module(normalized, module_index):
            continue
        model.modules.append(normalized)
        model.raw_module_map[normalized] = normalized
        for alias, target in bindings.import_aliases:
            if alias and target:
                model.import_aliases.setdefault(alias, target)
        for alias, target in bindings.member_aliases:
            if alias and target:
                model.member_aliases.setdefault(alias, target)
        for target in bindings.static_wildcard_targets:
            if target:
                model.static_wildcard_targets.add(target)
    return model


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


def is_wildcard_import(node, content: bytes) -> bool:
    _ = content
    return any(getattr(child, "type", "") == "asterisk" for child in getattr(node, "children", []))


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
