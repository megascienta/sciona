# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord


@dataclass
class JavaNodeState:
    class_stack: List[str] = field(default_factory=list)
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
    if node is None:
        return None
    return content[node.start_byte : node.end_byte].decode("utf-8")


def _java_annotations(node, content: bytes) -> list[str]:
    annotations: list[str] = []
    modifiers = node.child_by_field_name("modifiers")
    if modifiers is None:
        return annotations
    for child in getattr(modifiers, "named_children", []):
        if child.type not in {"annotation", "marker_annotation"}:
            continue
        value = _node_text(child, content)
        if value:
            annotations.append(value)
    return annotations


def _java_bases(node, content: bytes) -> list[str]:
    bases: list[str] = []
    superclass = node.child_by_field_name("superclass")
    if superclass is not None:
        for child in getattr(superclass, "named_children", []):
            value = _node_text(child, content)
            if value:
                bases.append(value)
    interfaces = node.child_by_field_name("interfaces")
    if interfaces is not None:
        for child in getattr(interfaces, "named_children", []):
            value = _node_text(child, content)
            if value:
                bases.append(value)
    return bases


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
        class_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
        if state.class_stack:
            parent = state.class_stack[-1]
            parent_node_type = "class"
            qualified = f"{parent}.{class_name}"
        else:
            parent = module_name
            parent_node_type = "module"
            qualified = f"{module_name}.{class_name}"
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type="class",
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
                    "annotations": _java_annotations(node, snapshot.content),
                },
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=parent_node_type,
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type="class",
                dst_qualified_name=qualified,
                edge_type="CONTAINS",
            )
        )
        if parent_node_type == "class":
            result.edges.append(
                EdgeRecord(
                    src_language=language,
                    src_node_type=parent_node_type,
                    src_qualified_name=parent,
                    dst_language=language,
                    dst_node_type="class",
                    dst_qualified_name=qualified,
                    edge_type="NESTS",
                )
            )
        body = node.child_by_field_name("body")
        state.class_stack.append(qualified)
        state.class_methods.setdefault(qualified, set())
        state.class_name_map.setdefault(class_name, qualified)
        state.class_name_candidates.setdefault(class_name, set()).add(qualified)
        state.class_kind_map[qualified] = class_kind_map.get(node.type, "class")
        if body:
            for child in body.named_children:
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
        func_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
        if not state.class_stack:
            return
        node_type = "method"
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
                    "annotations": _java_annotations(node, snapshot.content),
                },
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type="class",
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type=node_type,
                dst_qualified_name=qualified,
                edge_type="DEFINES_METHOD",
            )
        )
        if node.type in {"constructor_declaration", "compact_constructor_declaration"}:
            constructor_fields = collect_constructor_field_types(body_node, snapshot)
            for field_name, type_text in constructor_fields.items():
                state.class_field_types.setdefault(parent, {})[field_name] = type_text
        state.pending_calls.append((qualified, node_type, body_node, parent))
        return

    if node.type == "field_declaration" and state.class_stack:
        class_name = state.class_stack[-1]
        for name, type_text in collect_declared_vars(node, snapshot):
            state.class_field_types.setdefault(class_name, {})[name] = type_text
        return

    for child in getattr(node, "named_children", []):
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
