# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord
from .type_names import type_base_name


@dataclass
class TypeScriptNodeState:
    class_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    class_name_candidates: dict[str, set[str]] = field(default_factory=dict)
    instance_map: dict[str, str] = field(default_factory=dict)
    class_instance_map: dict[str, dict[str, str]] = field(default_factory=dict)
    pending_instance_assignments: list[tuple[str, str]] = field(default_factory=list)
    pending_class_instances: list[tuple[str, str, str]] = field(default_factory=list)
    pending_alias_assignments: list[tuple[str, str]] = field(default_factory=list)
    pending_class_aliases: list[tuple[str, str, str]] = field(default_factory=list)
    pending_calls: list[tuple[str, str, object | None, str | None]] = field(
        default_factory=list
    )


def walk_typescript_nodes(
    node,
    *,
    language: str,
    snapshot: FileSnapshot,
    module_name: str,
    result,
    state: TypeScriptNodeState,
    function_depth: int,
) -> None:
    if node.type in {
        "class_declaration",
        "abstract_class_declaration",
        "interface_declaration",
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
            )
        )
        state.class_name_map.setdefault(class_name, qualified)
        state.class_name_candidates.setdefault(class_name, set()).add(qualified)
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
        body = node.child_by_field_name("body")
        state.class_stack.append(qualified)
        state.class_methods.setdefault(qualified, set())
        if body:
            for child in body.named_children:
                walk_typescript_nodes(
                    child,
                    language=language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                    function_depth=function_depth,
                )
        state.class_stack.pop()
        return

    if node.type in {
        "function_declaration",
        "method_definition",
        "method_signature",
        "abstract_method_signature",
    }:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        func_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
        if node.type in {"method_definition", "method_signature", "abstract_method_signature"}:
            if not state.class_stack:
                return
            node_type = "method"
            parent = state.class_stack[-1]
            parent_node_type = "class"
            qualified = f"{parent}.{func_name}"
            edge_type = "DEFINES_METHOD"
            state.class_methods.setdefault(parent, set()).add(func_name)
        else:
            if function_depth > 0:
                return
            node_type = "function"
            parent = module_name
            parent_node_type = "module"
            qualified = f"{module_name}.{func_name}"
            edge_type = "CONTAINS"
            state.module_functions.add(func_name)
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
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=parent_node_type,
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type=node_type,
                dst_qualified_name=qualified,
                edge_type=edge_type,
            )
        )
        body_node = node.child_by_field_name("body")
        if node.type == "method_definition" and func_name == "constructor" and state.class_stack:
            for field_name, type_name in typed_constructor_parameters(node, snapshot.content):
                state.pending_class_instances.append((state.class_stack[-1], field_name, type_name))
        if node.type not in {"method_signature", "abstract_method_signature"}:
            state.pending_calls.append(
                (
                    qualified,
                    node_type,
                    body_node,
                    state.class_stack[-1] if state.class_stack else None,
                )
            )
        walk_typescript_children(
            node,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
            function_depth=function_depth,
        )
        return

    if node.type == "variable_declarator" and not state.class_stack and function_depth == 0:
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if not name_node or not value_node:
            return
        if value_node.type in {"class", "class_expression"} and name_node.type == "identifier":
            class_name = snapshot.content[
                name_node.start_byte : name_node.end_byte
            ].decode("utf-8")
            qualified = f"{module_name}.{class_name}"
            result.nodes.append(
                SemanticNodeRecord(
                    language=language,
                    node_type="class",
                    qualified_name=qualified,
                    display_name=class_name,
                    file_path=snapshot.record.relative_path,
                    start_line=value_node.start_point[0] + 1,
                    end_line=value_node.end_point[0] + 1,
                    start_byte=value_node.start_byte,
                    end_byte=value_node.end_byte,
                )
            )
            result.edges.append(
                EdgeRecord(
                    src_language=language,
                    src_node_type="module",
                    src_qualified_name=module_name,
                    dst_language=language,
                    dst_node_type="class",
                    dst_qualified_name=qualified,
                    edge_type="CONTAINS",
                )
            )
            state.class_name_map.setdefault(class_name, qualified)
            state.class_name_candidates.setdefault(class_name, set()).add(qualified)
            state.class_stack.append(qualified)
            state.class_methods.setdefault(qualified, set())
            body = value_node.child_by_field_name("body")
            if body:
                for child in body.named_children:
                    walk_typescript_nodes(
                        child,
                        language=language,
                        snapshot=snapshot,
                        module_name=module_name,
                        result=result,
                        state=state,
                        function_depth=function_depth,
                    )
            state.class_stack.pop()
            return
        if value_node.type == "new_expression":
            if name_node.type == "identifier":
                callee = value_node.child_by_field_name("constructor") or value_node.child_by_field_name(
                    "function"
                )
                callee_text = node_text(callee, snapshot.content)
                name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8"
                )
                if callee_text and name:
                    state.pending_instance_assignments.append((name, callee_text))
            return
        if value_node.type == "identifier" and name_node.type == "identifier":
            name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
                "utf-8"
            )
            source = snapshot.content[
                value_node.start_byte : value_node.end_byte
            ].decode("utf-8")
            if name and source:
                state.pending_alias_assignments.append((name, source))
            return
        if value_node.type not in {"arrow_function", "function", "function_expression"}:
            return
        if name_node.type != "identifier":
            return
        func_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
        qualified = f"{module_name}.{func_name}"
        state.module_functions.add(func_name)
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type="function",
                qualified_name=qualified,
                display_name=func_name,
                file_path=snapshot.record.relative_path,
                start_line=value_node.start_point[0] + 1,
                end_line=value_node.end_point[0] + 1,
                start_byte=value_node.start_byte,
                end_byte=value_node.end_byte,
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type="module",
                src_qualified_name=module_name,
                dst_language=language,
                dst_node_type="function",
                dst_qualified_name=qualified,
                edge_type="CONTAINS",
            )
        )
        state.pending_calls.append((qualified, "function", function_body_node(value_node), None))
        return

    if node.type in {
        "public_field_definition",
        "private_field_definition",
        "property_definition",
        "field_definition",
    } and state.class_stack:
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if not name_node:
            return
        field = snapshot.content[name_node.start_byte : name_node.end_byte].decode("utf-8")
        type_node = node.child_by_field_name("type")
        type_name = parse_type_annotation(type_node, snapshot.content)
        if type_name and field and (value_node is None or value_node.type != "new_expression"):
            state.pending_class_instances.append((state.class_stack[-1], field, type_name))
        if value_node is None:
            return
        if value_node.type == "new_expression":
            if name_node.type == "property_identifier":
                callee = value_node.child_by_field_name("constructor") or value_node.child_by_field_name(
                    "function"
                )
                callee_text = node_text(callee, snapshot.content)
                if callee_text and field:
                    state.pending_class_instances.append(
                        (state.class_stack[-1], field, callee_text)
                    )
            return
        if value_node.type not in {"arrow_function", "function", "function_expression"}:
            return
        if name_node.type != "property_identifier":
            return
        func_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
        parent = state.class_stack[-1]
        qualified = f"{parent}.{func_name}"
        state.class_methods.setdefault(parent, set()).add(func_name)
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type="method",
                qualified_name=qualified,
                display_name=func_name,
                file_path=snapshot.record.relative_path,
                start_line=value_node.start_point[0] + 1,
                end_line=value_node.end_point[0] + 1,
                start_byte=value_node.start_byte,
                end_byte=value_node.end_byte,
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type="class",
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type="method",
                dst_qualified_name=qualified,
                edge_type="DEFINES_METHOD",
            )
        )
        state.pending_calls.append((qualified, "method", function_body_node(value_node), parent))
        return

    if node.type == "assignment_expression" and state.class_stack and function_depth > 0:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if left is not None and right is not None and right.type == "new_expression":
            if left.type in {"member_expression", "subscript_expression"}:
                object_node = left.child_by_field_name("object")
                property_node = left.child_by_field_name("property")
                object_name = node_text(object_node, snapshot.content) or ""
                field = node_text(property_node, snapshot.content) or ""
                if object_name == "this" and field:
                    callee = right.child_by_field_name(
                        "constructor"
                    ) or right.child_by_field_name("function")
                    callee_text = node_text(callee, snapshot.content)
                    if callee_text:
                        state.pending_class_instances.append(
                            (state.class_stack[-1], field, callee_text)
                        )
        elif (
            left is not None
            and right is not None
            and left.type in {"member_expression", "subscript_expression"}
            and right.type == "member_expression"
        ):
            object_node = left.child_by_field_name("object")
            property_node = left.child_by_field_name("property")
            object_name = node_text(object_node, snapshot.content) or ""
            field = node_text(property_node, snapshot.content) or ""
            if object_name == "this" and field:
                rhs = node_text(right, snapshot.content) or ""
                if rhs.startswith("this."):
                    rhs_field = rhs.split(".", 1)[1]
                    if rhs_field:
                        state.pending_class_aliases.append(
                            (state.class_stack[-1], field, rhs_field)
                        )

    walk_typescript_children(
        node,
        language=language,
        snapshot=snapshot,
        module_name=module_name,
        result=result,
        state=state,
        function_depth=function_depth,
    )


def walk_typescript_children(
    node,
    *,
    language: str,
    snapshot: FileSnapshot,
    module_name: str,
    result,
    state: TypeScriptNodeState,
    function_depth: int,
) -> None:
    next_depth = (
        function_depth + 1
        if node.type
        in {
            "function",
            "function_expression",
            "arrow_function",
            "method_definition",
            "function_declaration",
        }
        else function_depth
    )
    for child in getattr(node, "named_children", []):
        walk_typescript_nodes(
            child,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
            function_depth=next_depth,
        )


def function_body_node(node) -> object | None:
    if node is None:
        return None
    return node.child_by_field_name("body") or node


def node_text(node, content: bytes) -> str | None:
    if node is None:
        return None
    text = getattr(node, "text", None)
    if text:
        return text.decode("utf-8")
    return content[node.start_byte : node.end_byte].decode("utf-8")


def parse_type_annotation(node, content: bytes) -> str | None:
    text = node_text(node, content)
    if not text:
        return None
    normalized = type_base_name(text)
    return normalized or None


def typed_constructor_parameters(node, content: bytes) -> list[tuple[str, str]]:
    params = node.child_by_field_name("parameters")
    if params is None:
        return []
    typed: list[tuple[str, str]] = []
    for child in getattr(params, "children", []):
        if child.type not in {"required_parameter", "optional_parameter"}:
            continue
        name_node = child.child_by_field_name("pattern") or child.child_by_field_name("name")
        if name_node is None:
            name_node = next(
                (c for c in getattr(child, "children", []) if c.type == "identifier"),
                None,
            )
        type_node = child.child_by_field_name("type")
        name = node_text(name_node, content) if name_node else None
        type_name = parse_type_annotation(type_node, content)
        if name and type_name:
            typed.append((name, type_name))
    return typed
