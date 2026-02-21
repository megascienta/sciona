# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord


@dataclass
class TypeScriptNodeState:
    class_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    instance_map: dict[str, str] = field(default_factory=dict)
    class_instance_map: dict[str, dict[str, str]] = field(default_factory=dict)
    pending_instance_assignments: list[tuple[str, str]] = field(default_factory=list)
    pending_class_instances: list[tuple[str, str, str]] = field(default_factory=list)
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
    if node.type == "class_declaration":
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
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
        state.class_name_map[class_name] = qualified
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
        body = node.child_by_field_name("body")
        state.class_stack.append(qualified)
        state.class_methods.setdefault(qualified, set())
        if body:
            for child in body.children:
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

    if node.type in {"function_declaration", "method_definition"}:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        func_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
        if node.type == "method_definition":
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
            function_depth=function_depth + 1,
        )
        return

    if node.type == "variable_declarator" and not state.class_stack and function_depth == 0:
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if not name_node or not value_node:
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
        if not name_node or not value_node:
            return
        if value_node.type == "new_expression":
            if name_node.type == "property_identifier":
                callee = value_node.child_by_field_name("constructor") or value_node.child_by_field_name(
                    "function"
                )
                callee_text = node_text(callee, snapshot.content)
                field = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8"
                )
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
    for child in getattr(node, "children", []):
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
    return content[node.start_byte : node.end_byte].decode("utf-8")
