# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Walker implementation for TypeScript node extraction."""

from __future__ import annotations
import re

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord
from ..utils import find_direct_children_query
from .typescript_node_state import TypeScriptNodeState
from .typescript_node_text import (
    function_body_node,
    name_chain,
    node_text,
    parse_type_annotation,
    typed_constructor_parameters,
)


def _decorator_names(node, content: bytes) -> list[str]:
    parent = getattr(node, "parent", None)
    if parent is None:
        return []
    siblings = list(getattr(parent, "named_children", []))
    decorators: list[str] = []
    node_key = (node.start_byte, node.end_byte, node.type)
    for index, child in enumerate(siblings):
        child_key = (child.start_byte, child.end_byte, child.type)
        if child_key != node_key:
            continue
        for candidate in reversed(siblings[:index]):
            if candidate.type != "decorator":
                break
            text = node_text(candidate, content)
            if text:
                decorators.append(text)
        decorators.reverse()
        return decorators
    # Fallback for nodes where decorators are direct children.
    decorators: list[str] = []
    for child in getattr(node, "named_children", []):
        if child.type != "decorator":
            continue
        text = node_text(child, content)
        if text:
            decorators.append(text)
    return decorators


def _typescript_bases(node, content: bytes) -> list[str]:
    heritage = node.child_by_field_name("heritage")
    if heritage is None:
        return []
    bases: list[str] = []
    for child in getattr(heritage, "named_children", []):
        value = node_text(child, content)
        if value:
            bases.append(value)
    return bases


def _decorator_qname(module_name: str, decorator_text: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", decorator_text).strip("_") or "decorator"
    return f"{module_name}.__decorator__.{token}"


def _emit_decorator_edges(
    *,
    language: str,
    snapshot: FileSnapshot,
    module_name: str,
    result,
    owner_qname: str,
    owner_type: str,
    decorators: list[str],
) -> None:
    if not decorators:
        return
    existing = {node.qualified_name for node in result.nodes if node.node_type == "decorator"}
    for decorator in decorators:
        decorator_qname = _decorator_qname(module_name, decorator)
        if decorator_qname not in existing:
            existing.add(decorator_qname)
            result.nodes.append(
                SemanticNodeRecord(
                    language=language,
                    node_type="decorator",
                    qualified_name=decorator_qname,
                    display_name=decorator,
                    file_path=snapshot.record.relative_path,
                    start_line=1,
                    end_line=1,
                    start_byte=0,
                    end_byte=0,
                )
            )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=owner_type,
                src_qualified_name=owner_qname,
                dst_language=language,
                dst_node_type="decorator",
                dst_qualified_name=decorator_qname,
                edge_type="DECORATED_BY",
            )
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
    class_kind_map = {
        "class_declaration": "class",
        "abstract_class_declaration": "class",
        "interface_declaration": "interface",
    }
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
                metadata={
                    "kind": class_kind_map.get(node.type, "class"),
                    "bases": _typescript_bases(node, snapshot.content),
                    "decorators": _decorator_names(node, snapshot.content),
                },
            )
        )
        _emit_decorator_edges(
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            owner_qname=qualified,
            owner_type="class",
            decorators=_decorator_names(node, snapshot.content),
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
        if body:
            for child in find_direct_children_query(body, language_name="typescript"):
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
                metadata=(
                    None
                    if node_type != "method"
                    else {
                        "kind": "method",
                        "signature_only": node.type
                        in {"method_signature", "abstract_method_signature"},
                        "abstract": node.type == "abstract_method_signature",
                        "decorators": _decorator_names(node, snapshot.content),
                    }
                ),
            )
        )
        _emit_decorator_edges(
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            owner_qname=qualified,
            owner_type=node_type,
            decorators=_decorator_names(node, snapshot.content),
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
            function_depth=function_depth + (1 if node.type == "function_declaration" else 0),
        )
        return

    if node.type == "variable_declarator" and not state.class_stack and function_depth == 0:
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if not name_node or not value_node:
            return
        if name_node.type == "identifier":
            binding = node_text(name_node, snapshot.content)
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
                    metadata={"kind": "class", "bases": [], "decorators": []},
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
                for child in find_direct_children_query(body, language_name="typescript"):
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
                callee_chain = name_chain(callee, snapshot.content)
                name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
                    "utf-8"
                )
                if callee_chain and name:
                    state.pending_instance_assignments.append((name, callee_chain))
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
                callee_chain = name_chain(callee, snapshot.content)
                if callee_chain and field:
                    state.pending_class_instances.append(
                        (state.class_stack[-1], field, callee_chain)
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
                    callee_chain = name_chain(callee, snapshot.content)
                    if callee_chain:
                        state.pending_class_instances.append(
                            (state.class_stack[-1], field, callee_chain)
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
        }
        else function_depth
    )
    for child in find_direct_children_query(node, language_name="typescript"):
        walk_typescript_nodes(
            child,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
            function_depth=next_depth,
        )


__all__ = ["walk_typescript_children", "walk_typescript_nodes"]
