# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord
from ..query_helpers import find_nodes_of_types_query
from .query_surface import JAVA_STRUCTURAL_NODE_TYPES
from .shared import node_text as shared_node_text


@dataclass
class JavaNodeState:
    class_stack: List[str] = field(default_factory=list)
    callable_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    class_name_candidates: dict[str, set[str]] = field(default_factory=dict)
    class_kind_map: dict[str, str] = field(default_factory=dict)
    class_field_types: dict[str, dict[str, str]] = field(default_factory=dict)
    pending_calls: list[tuple[str, str, object | None, str | None]] = field(
        default_factory=list
    )


def _node_text(node, content: bytes) -> str | None:
    return shared_node_text(node, content)


def _query_direct_type_names(node, content: bytes) -> list[str]:
    if node is None:
        return []
    captured = find_nodes_of_types_query(
        node,
        language_name="java",
        node_types=("type_identifier", "scoped_type_identifier", "generic_type"),
    )
    names: list[str] = []
    seen: set[str] = set()
    for child in captured:
        value = _node_text(child, content)
        if value:
            if value in seen:
                continue
            seen.add(value)
            names.append(value)
    return names


def _java_bases(node, content: bytes) -> list[str]:
    bases: list[str] = []
    superclass = node.child_by_field_name("superclass")
    if superclass is not None:
        bases.extend(_query_direct_type_names(superclass, content))
    interfaces = node.child_by_field_name("interfaces")
    if interfaces is not None:
        bases.extend(_query_direct_type_names(interfaces, content))
    return bases


def _java_structural_children(node) -> list[object]:
    return [
        child
        for child in getattr(node, "named_children", [])
        if getattr(child, "type", "") in JAVA_STRUCTURAL_NODE_TYPES
    ]


def walk_java_nodes(
    node,
    *,
    language: str,
    snapshot: FileSnapshot,
    module_name: str,
    result,
    state: JavaNodeState,
    collect_declared_vars,
    collect_constructor_field_types,
) -> None:
    class_kind_map = {
        "class_declaration": "class",
        "interface_declaration": "interface",
        "enum_declaration": "enum",
        "record_declaration": "record",
    }
    if node.type in {
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "record_declaration",
    }:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = _node_text(name_node, snapshot.content)
        if not class_name:
            return
        if state.class_stack:
            parent = state.class_stack[-1]
            parent_node_type = "type"
            qualified = f"{parent}.{class_name}"
        elif state.callable_stack:
            parent = state.callable_stack[-1]
            parent_node_type = "callable"
            qualified = f"{parent}.{class_name}"
        else:
            parent = module_name
            parent_node_type = "module"
            qualified = f"{module_name}.{class_name}"
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type="type",
                qualified_name=qualified,
                display_name=class_name,
                file_path=snapshot.record.relative_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                metadata={
                    "kind": class_kind_map.get(node.type, "class"),
                    "bases": _java_bases(node, snapshot.content),
                },
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=parent_node_type,
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type="type",
                dst_qualified_name=qualified,
                edge_type="LEXICALLY_CONTAINS",
            )
        )
        body = node.child_by_field_name("body")
        state.class_stack.append(qualified)
        state.class_methods.setdefault(qualified, set())
        state.class_name_map.setdefault(class_name, qualified)
        state.class_name_candidates.setdefault(class_name, set()).add(qualified)
        state.class_kind_map[qualified] = class_kind_map.get(node.type, "class")
        if body:
            for child in _java_structural_children(body):
                walk_java_nodes(
                    child,
                    language=language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                    collect_declared_vars=collect_declared_vars,
                    collect_constructor_field_types=collect_constructor_field_types,
                )
        state.class_stack.pop()
        return

    if node.type in {
        "method_declaration",
        "constructor_declaration",
        "compact_constructor_declaration",
    }:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        func_name = _node_text(name_node, snapshot.content)
        if not func_name:
            return
        if not state.class_stack:
            return
        node_type = "callable"
        parent = state.class_stack[-1]
        state.class_methods.setdefault(parent, set()).add(func_name)
        qualified = f"{parent}.{func_name}"
        callable_kind = {
            "constructor_declaration": "constructor",
            "compact_constructor_declaration": "compact_constructor",
            "method_declaration": "method",
        }.get(node.type, "method")
        body_node = node.child_by_field_name("body")
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type=node_type,
                qualified_name=qualified,
                display_name=func_name,
                file_path=snapshot.record.relative_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                metadata={
                    "kind": callable_kind,
                    "declared_in_kind": state.class_kind_map.get(parent, "class"),
                    "abstract": node.type == "method_declaration" and body_node is None,
                },
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type="type",
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type=node_type,
                dst_qualified_name=qualified,
                edge_type="LEXICALLY_CONTAINS",
            )
        )
        if node.type in {"constructor_declaration", "compact_constructor_declaration"}:
            constructor_fields = collect_constructor_field_types(body_node, snapshot)
            for field_name, type_text in constructor_fields.items():
                state.class_field_types.setdefault(parent, {})[field_name] = type_text
        metadata = result.nodes[-1].metadata or {}
        if "constructor" in callable_kind:
            role = "constructor"
        elif state.callable_stack:
            role = "nested"
        else:
            role = "declared"
        metadata["callable_role"] = role
        result.nodes[-1].metadata = metadata
        state.pending_calls.append((qualified, node_type, body_node, parent))
        state.callable_stack.append(qualified)
        if body_node:
            for child in _java_structural_children(body_node):
                walk_java_nodes(
                    child,
                    language=language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                    collect_declared_vars=collect_declared_vars,
                    collect_constructor_field_types=collect_constructor_field_types,
                )
        state.callable_stack.pop()
        return

    if node.type == "field_declaration" and state.class_stack:
        class_name = state.class_stack[-1]
        for name, type_text in collect_declared_vars(node, snapshot):
            state.class_field_types.setdefault(class_name, {})[name] = type_text
        return

    for child in _java_structural_children(node):
        walk_java_nodes(
            child,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
            collect_declared_vars=collect_declared_vars,
            collect_constructor_field_types=collect_constructor_field_types,
        )
