# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript import extraction utilities."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Optional

from ....core.module_naming import module_name_from_path
from ....core.normalize_model import FileSnapshot
from ....core.extract.parsing.query_helpers import find_nodes_of_types_query
from ...common.ir.import_model import NormalizedImportModel
from ...common.query.query_surface import (
    JAVASCRIPT_DYNAMIC_IMPORT_NODE_TYPES,
    JAVASCRIPT_IMPORT_EXPORT_NODE_TYPES,
    JAVASCRIPT_REQUIRE_DECLARATION_NODE_TYPES,
    TYPESCRIPT_STRING_NODE_TYPES,
)
from ...common.support.shared import is_internal_module, repo_root_from_snapshot


def collect_javascript_import_model(
    root,
    snapshot,
    module_name: str,
    *,
    module_index,
) -> NormalizedImportModel:
    del module_name
    model = NormalizedImportModel()
    nodes = find_nodes_of_types_query(
        root,
        language_name="javascript",
        node_types=JAVASCRIPT_IMPORT_EXPORT_NODE_TYPES,
    )
    for node in nodes:
        model.imports_seen += 1
        module_spec = extract_module_spec_from_node(node, snapshot.content)
        if not module_spec:
            continue
        normalized = normalize_import(module_spec, snapshot)
        if not normalized or not is_internal_module(normalized, module_index):
            if module_index is not None and module_spec.strip().startswith("."):
                alt = normalize_relative_index(module_spec, snapshot)
                if alt and is_internal_module(alt, module_index):
                    normalized = alt
                else:
                    if module_index is not None:
                        model.imports_filtered_not_internal += 1
                    continue
            else:
                if module_index is not None and normalized:
                    model.imports_filtered_not_internal += 1
                continue
        model.imports_internal += 1
        model.modules.append(normalized)
        populate_js_aliases_from_node(
            node,
            snapshot.content,
            normalized,
            model.import_aliases,
            model.member_aliases,
        )
    for node in find_nodes_of_types_query(
        root,
        language_name="javascript",
        node_types=JAVASCRIPT_REQUIRE_DECLARATION_NODE_TYPES,
    ):
        model.imports_seen += 1
        alias, module_spec = extract_require_assignment_from_node(node, snapshot.content)
        if not alias or not module_spec:
            continue
        normalized = normalize_import(module_spec, snapshot)
        if not normalized or not is_internal_module(normalized, module_index):
            if module_index is not None and module_spec.strip().startswith("."):
                alt = normalize_relative_index(module_spec, snapshot)
                if alt and is_internal_module(alt, module_index):
                    normalized = alt
                else:
                    if module_index is not None:
                        model.imports_filtered_not_internal += 1
                    continue
            else:
                if module_index is not None and normalized:
                    model.imports_filtered_not_internal += 1
                continue
        model.imports_internal += 1
        model.modules.append(normalized)
        model.import_aliases[alias] = normalized
    for node in find_nodes_of_types_query(
        root,
        language_name="javascript",
        node_types=JAVASCRIPT_DYNAMIC_IMPORT_NODE_TYPES,
    ):
        module_spec = extract_dynamic_import_spec_from_call(node, snapshot.content)
        if not module_spec:
            continue
        model.imports_seen += 1
        normalized = normalize_import(module_spec, snapshot)
        if not normalized or not is_internal_module(normalized, module_index):
            if module_index is not None and module_spec.strip().startswith("."):
                alt = normalize_relative_index(module_spec, snapshot)
                if alt and is_internal_module(alt, module_index):
                    normalized = alt
                else:
                    if module_index is not None:
                        model.imports_filtered_not_internal += 1
                    continue
            else:
                if module_index is not None and normalized:
                    model.imports_filtered_not_internal += 1
                continue
        model.imports_internal += 1
        model.modules.append(normalized)
    return model


def extract_module_spec_from_node(node, content: bytes) -> Optional[str]:
    source = node.child_by_field_name("source")
    if source is not None:
        return decode_string_literal(source, content)
    for child in getattr(node, "children", []):
        if child.type == "import_require_clause":
            for candidate in getattr(child, "children", []):
                if candidate.type == "string":
                    return decode_string_literal(candidate, content)
    string_nodes = find_nodes_of_types_query(
        node,
        language_name="javascript",
        node_types=TYPESCRIPT_STRING_NODE_TYPES,
    )
    if string_nodes:
        return decode_string_literal(string_nodes[0], content)
    return None


def extract_dynamic_import_spec_from_call(node, content: bytes) -> Optional[str]:
    function_node = node.child_by_field_name("function")
    if function_node is None:
        return None
    callee = content[function_node.start_byte : function_node.end_byte].decode("utf-8").strip()
    if callee != "import":
        return None
    args_node = node.child_by_field_name("arguments")
    if args_node is None:
        return None
    first_literal = next(
        (
            child
            for child in getattr(args_node, "children", [])
            if child.type in TYPESCRIPT_STRING_NODE_TYPES
        ),
        None,
    )
    if first_literal is None:
        return None
    return decode_string_literal(first_literal, content)


def decode_string_literal(node, content: bytes) -> Optional[str]:
    text = content[node.start_byte : node.end_byte].decode("utf-8").strip()
    if not text:
        return None
    if node.type == "template_string":
        if "${" in text:
            return None
        return text.strip("`")
    return text.strip("'\"")


def populate_js_aliases_from_node(
    node,
    content: bytes,
    normalized: str,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    if node.type == "import_statement":
        for child in getattr(node, "children", []):
            if child.type == "import_clause":
                _populate_import_clause_aliases(
                    child, content, normalized, import_aliases, member_aliases
                )
            if child.type == "import_require_clause":
                alias = _first_identifier(child, content)
                if alias:
                    import_aliases[alias] = normalized
    if node.type == "export_statement":
        for child in getattr(node, "children", []):
            if child.type == "export_clause":
                _populate_export_clause_aliases(child, content, normalized, member_aliases)


def _populate_import_clause_aliases(
    import_clause,
    content: bytes,
    normalized: str,
    import_aliases: dict[str, str],
    member_aliases: dict[str, str],
) -> None:
    for child in getattr(import_clause, "children", []):
        if child.type == "identifier":
            alias = content[child.start_byte : child.end_byte].decode("utf-8").strip()
            if alias:
                import_aliases[alias] = normalized
        elif child.type == "namespace_import":
            alias = _last_identifier(child, content)
            if alias:
                import_aliases[alias] = normalized
        elif child.type == "named_imports":
            for spec in getattr(child, "children", []):
                if spec.type != "import_specifier":
                    continue
                name, alias = _specifier_name_alias(spec, content)
                if name:
                    member_aliases[alias or name] = f"{normalized}.{name}"


def _populate_export_clause_aliases(
    export_clause,
    content: bytes,
    normalized: str,
    member_aliases: dict[str, str],
) -> None:
    for child in getattr(export_clause, "children", []):
        if child.type != "export_specifier":
            continue
        name, alias = _specifier_name_alias(child, content)
        if name:
            member_aliases[alias or name] = f"{normalized}.{name}"


def _specifier_name_alias(node, content: bytes) -> tuple[str | None, str | None]:
    identifiers = [
        content[ch.start_byte : ch.end_byte].decode("utf-8").strip()
        for ch in getattr(node, "children", [])
        if ch.type == "identifier"
    ]
    if not identifiers:
        return None, None
    if len(identifiers) == 1:
        return identifiers[0], None
    return identifiers[0], identifiers[-1]


def _first_identifier(node, content: bytes) -> str | None:
    for child in getattr(node, "children", []):
        if child.type == "identifier":
            alias = content[child.start_byte : child.end_byte].decode("utf-8").strip()
            return alias or None
    return None


def _last_identifier(node, content: bytes) -> str | None:
    identifiers = [
        content[child.start_byte : child.end_byte].decode("utf-8").strip()
        for child in getattr(node, "children", [])
        if child.type == "identifier"
    ]
    if not identifiers:
        return None
    return identifiers[-1] or None


def extract_require_assignment_from_node(
    node,
    content: bytes,
) -> tuple[str | None, str | None]:
    for child in getattr(node, "children", []):
        if child.type != "variable_declarator":
            continue
        name_node = child.child_by_field_name("name")
        value_node = child.child_by_field_name("value")
        if (
            name_node is None
            or value_node is None
            or value_node.type != "call_expression"
        ):
            continue
        callee_node = value_node.child_by_field_name("function")
        if callee_node is None:
            continue
        callee = content[callee_node.start_byte : callee_node.end_byte].decode("utf-8").strip()
        if callee != "require":
            continue
        args = value_node.child_by_field_name("arguments")
        if args is None:
            continue
        string_node = next(
            (arg for arg in getattr(args, "children", []) if arg.type == "string"),
            None,
        )
        if string_node is None:
            continue
        alias = content[name_node.start_byte : name_node.end_byte].decode("utf-8").strip()
        module = decode_string_literal(string_node, content)
        return (alias or None, module)
    return None, None


def normalize_import(specifier: Optional[str], snapshot: FileSnapshot) -> Optional[str]:
    if not specifier:
        return None
    spec = specifier.strip().strip("'\"")
    if not spec:
        return None
    if spec.startswith("."):
        parent = PurePosixPath(snapshot.record.relative_path.parent.as_posix())
        normalized = normalize_relative_path(parent, PurePosixPath(spec))
        if normalized is None:
            return None
        module_path = normalize_js_path(normalized.as_posix())
        repo_root = repo_root_from_snapshot(snapshot)
        return module_name_from_path(
            repo_root,
            Path(module_path),
            strip_suffix=False,
            treat_init_as_package=False,
        )
    return spec


def normalize_relative_index(specifier: str, snapshot: FileSnapshot) -> Optional[str]:
    spec = specifier.strip().strip("'\"")
    if not spec.startswith("."):
        return None
    parent = PurePosixPath(snapshot.record.relative_path.parent.as_posix())
    normalized = normalize_relative_path(parent, PurePosixPath(spec))
    if normalized is None:
        return None
    index_path = normalized / "index"
    module_path = normalize_js_path(index_path.as_posix())
    repo_root = repo_root_from_snapshot(snapshot)
    return module_name_from_path(
        repo_root,
        Path(module_path),
        strip_suffix=False,
        treat_init_as_package=False,
    )


def normalize_relative_path(
    base: PurePosixPath, relative: PurePosixPath
) -> PurePosixPath | None:
    parts = list(base.parts)
    for part in relative.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
                continue
            return None
        parts.append(part)
    return PurePosixPath(*parts)


def normalize_js_path(path: str) -> str:
    name = path
    if name.endswith(".mjs"):
        name = name[: -len(".mjs")]
    elif name.endswith(".cjs"):
        name = name[: -len(".cjs")]
    elif name.endswith(".js"):
        name = name[: -len(".js")]
    return name


__all__ = ["collect_javascript_import_model"]
