# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Walker implementation for TypeScript node extraction."""

from __future__ import annotations

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord
from ..query_helpers import find_direct_children_query
from .typescript_node_state import TypeScriptNodeState
from .typescript_node_text import (
    function_body_node,
    name_chain,
    node_text,
    parse_type_annotation,
    typed_constructor_parameters,
)


def _span_encloses(parent: tuple[int, int], child: tuple[int, int]) -> bool:
    return parent[0] <= child[0] and parent[1] >= child[1]


def _typescript_bases(node, content: bytes) -> list[str]:
    heritage = node.child_by_field_name("heritage")
    if heritage is None:
        heritage = next(
            (
                child
                for child in getattr(node, "named_children", [])
                if child.type in {"class_heritage", "extends_clause", "implements_clause"}
            ),
            None,
        )
    if heritage is None:
        return []
    bases: list[str] = []
    for child in getattr(heritage, "named_children", []):
        value = node_text(child, content)
        if not value:
            continue
        value = value.strip()
        if value.startswith("extends "):
            value = value[len("extends ") :].strip()
        elif value.startswith("implements "):
            value = value[len("implements ") :].strip()
        for part in value.split(","):
            cleaned = part.strip()
            if cleaned:
                bases.append(cleaned)
    return bases


def _is_async_callable(node, content: bytes) -> bool:
    text = (node_text(node, content) or "").lstrip()
    return text.startswith("async ")


def _disambiguate_child_name(
    *,
    state: TypeScriptNodeState,
    parent: str,
    child_kind: str,
    local_name: str,
) -> str:
    return state.name_disambiguator.canonical_name(
        parent=parent,
        child_kind=child_kind,
        local_name=local_name,
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
    def _emit_bound_callable(
        *,
        name: str,
        value_node,
        parent: str,
        parent_node_type: str,
        class_name: str | None,
    ) -> None:
        if parent_node_type == "type" and state.class_span_stack:
            parent_span = state.class_span_stack[-1]
            child_span = (value_node.start_byte, value_node.end_byte)
            if not _span_encloses(parent_span, child_span):
                return
        emitted_name = _disambiguate_child_name(
            state=state,
            parent=parent,
            child_kind="callable",
            local_name=name,
        )
        qualified = f"{parent}.{emitted_name}"
        if parent_node_type == "module":
            state.module_functions.add(name)
        elif parent_node_type == "type":
            state.class_methods.setdefault(parent, set()).add(name)
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type="callable",
                qualified_name=qualified,
                display_name=name,
                file_path=snapshot.record.relative_path,
                start_line=value_node.start_point[0] + 1,
                end_line=value_node.end_point[0] + 1,
                start_byte=value_node.start_byte,
                end_byte=value_node.end_byte,
                metadata={
                    "kind": "async_callable"
                    if _is_async_callable(value_node, snapshot.content)
                    else "callable",
                    "callable_role": "bound",
                },
            )
        )
        result.edges.append(
            EdgeRecord(
                src_language=language,
                src_node_type=parent_node_type,
                src_qualified_name=parent,
                dst_language=language,
                dst_node_type="callable",
                dst_qualified_name=qualified,
                edge_type="LEXICALLY_CONTAINS",
            )
        )
        state.pending_calls.append((qualified, "callable", function_body_node(value_node), class_name))

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
        class_name = node_text(name_node, snapshot.content)
        if not class_name:
            return
        if state.callable_stack:
            parent = state.callable_stack[-1]
            parent_node_type = "callable"
        elif state.class_stack:
            parent = state.class_stack[-1]
            parent_node_type = "type"
        else:
            parent = module_name
            parent_node_type = "module"
        emitted_name = _disambiguate_child_name(
            state=state,
            parent=parent,
            child_kind="type",
            local_name=class_name,
        )
        qualified = f"{parent}.{emitted_name}"
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
                    "bases": _typescript_bases(node, snapshot.content),
                },
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
                dst_node_type="type",
                dst_qualified_name=qualified,
                edge_type="LEXICALLY_CONTAINS",
            )
        )
        body = node.child_by_field_name("body")
        state.class_stack.append(qualified)
        state.class_span_stack.append((node.start_byte, node.end_byte))
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
        state.class_span_stack.pop()
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
        func_name = node_text(name_node, snapshot.content)
        if not func_name:
            return
        if node.type in {"method_definition", "method_signature", "abstract_method_signature"}:
            if not state.class_stack:
                return
            if state.class_span_stack:
                parent_span = state.class_span_stack[-1]
                child_span = (node.start_byte, node.end_byte)
                if not _span_encloses(parent_span, child_span):
                    return
            node_type = "callable"
            parent = state.class_stack[-1]
            parent_node_type = "type"
            emitted_name = _disambiguate_child_name(
                state=state,
                parent=parent,
                child_kind="callable",
                local_name=func_name,
            )
            qualified = f"{parent}.{emitted_name}"
            edge_type = "LEXICALLY_CONTAINS"
            state.class_methods.setdefault(parent, set()).add(func_name)
            role = "constructor" if func_name == "constructor" else "declared"
        else:
            node_type = "callable"
            if state.callable_stack:
                parent = state.callable_stack[-1]
                parent_node_type = "callable"
                emitted_name = _disambiguate_child_name(
                    state=state,
                    parent=parent,
                    child_kind="callable",
                    local_name=func_name,
                )
                qualified = f"{parent}.{emitted_name}"
                role = "nested"
            else:
                parent = module_name
                parent_node_type = "module"
                emitted_name = _disambiguate_child_name(
                    state=state,
                    parent=parent,
                    child_kind="callable",
                    local_name=func_name,
                )
                qualified = f"{parent}.{emitted_name}"
                role = "declared"
            edge_type = "LEXICALLY_CONTAINS"
            if parent_node_type == "module":
                state.module_functions.add(func_name)
        is_async = _is_async_callable(node, snapshot.content)
        metadata = {
            "callable_role": role,
            "kind": "async_callable" if is_async else "callable",
            "signature_only": node.type in {"method_signature", "abstract_method_signature"},
            "abstract": node.type == "abstract_method_signature",
        }
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
                metadata=metadata,
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
        state.callable_stack.append(qualified)
        walk_typescript_children(
            node,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
            function_depth=function_depth + (1 if node.type == "function_declaration" else 0),
        )
        state.callable_stack.pop()
        return

    if node.type == "export_statement":
        value_node = node.child_by_field_name("value")
        if value_node is not None and value_node.type in {"arrow_function", "function", "function_expression"}:
            _emit_bound_callable(
                name="default",
                value_node=value_node,
                parent=module_name,
                parent_node_type="module",
                class_name=None,
            )
            return

    if node.type == "variable_declarator":
        name_node = node.child_by_field_name("name")
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if not name_node or not value_node:
            return
        if value_node.type in {"class", "class_expression"} and name_node.type == "identifier":
            class_name = node_text(name_node, snapshot.content)
            if not class_name:
                return
            if state.callable_stack:
                parent = state.callable_stack[-1]
                parent_node_type = "callable"
            elif state.class_stack:
                parent = state.class_stack[-1]
                parent_node_type = "type"
            else:
                parent = module_name
                parent_node_type = "module"
            emitted_name = _disambiguate_child_name(
                state=state,
                parent=parent,
                child_kind="type",
                local_name=class_name,
            )
            qualified = f"{parent}.{emitted_name}"
            result.nodes.append(
                SemanticNodeRecord(
                    language=language,
                    node_type="type",
                    qualified_name=qualified,
                    display_name=class_name,
                    file_path=snapshot.record.relative_path,
                    start_line=value_node.start_point[0] + 1,
                    end_line=value_node.end_point[0] + 1,
                    start_byte=value_node.start_byte,
                    end_byte=value_node.end_byte,
                    metadata={
                        "kind": "class",
                        "bases": _typescript_bases(value_node, snapshot.content),
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
            state.class_name_map.setdefault(class_name, qualified)
            state.class_name_candidates.setdefault(class_name, set()).add(qualified)
            state.class_stack.append(qualified)
            state.class_span_stack.append((value_node.start_byte, value_node.end_byte))
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
            state.class_span_stack.pop()
            return
        if value_node.type == "object" and name_node.type == "identifier":
            object_name = node_text(name_node, snapshot.content)
            if not object_name:
                return
            if state.callable_stack:
                parent = state.callable_stack[-1]
                parent_node_type = "callable"
                class_name = state.class_stack[-1] if state.class_stack else None
            elif state.class_stack:
                parent = state.class_stack[-1]
                parent_node_type = "type"
                class_name = parent
            else:
                parent = module_name
                parent_node_type = "module"
                class_name = None
            for child in find_direct_children_query(value_node, language_name="typescript"):
                if child.type == "method_definition":
                    method_name_node = child.child_by_field_name("name")
                    method_name = node_text(method_name_node, snapshot.content)
                    if not method_name:
                        continue
                    _emit_bound_callable(
                        name=f"{object_name}.{method_name}",
                        value_node=child,
                        parent=parent,
                        parent_node_type=parent_node_type,
                        class_name=class_name,
                    )
                elif child.type == "pair":
                    key_node = child.child_by_field_name("key")
                    method_name = node_text(key_node, snapshot.content) if key_node else None
                    member_value = child.child_by_field_name("value")
                    if not method_name or member_value is None:
                        continue
                    if member_value.type not in {"arrow_function", "function", "function_expression"}:
                        continue
                    _emit_bound_callable(
                        name=f"{object_name}.{method_name}",
                        value_node=member_value,
                        parent=parent,
                        parent_node_type=parent_node_type,
                        class_name=class_name,
                    )
            return
        if value_node.type == "new_expression":
            if name_node.type == "identifier":
                callee = value_node.child_by_field_name("constructor") or value_node.child_by_field_name(
                    "function"
                )
                callee_chain = name_chain(callee, snapshot.content)
                name = node_text(name_node, snapshot.content)
                if callee_chain and name:
                    state.pending_instance_assignments.append((name, callee_chain))
            return
        if value_node.type == "identifier" and name_node.type == "identifier":
            name = node_text(name_node, snapshot.content)
            source = node_text(value_node, snapshot.content)
            if name and source:
                state.pending_alias_assignments.append((name, source))
            return
        if value_node.type not in {"arrow_function", "function", "function_expression"}:
            return
        if name_node.type != "identifier":
            return
        func_name = node_text(name_node, snapshot.content)
        if not func_name:
            return
        if state.callable_stack:
            parent = state.callable_stack[-1]
            parent_node_type = "callable"
        elif state.class_stack:
            parent = state.class_stack[-1]
            parent_node_type = "type"
        else:
            parent = module_name
            parent_node_type = "module"
        _emit_bound_callable(
            name=func_name,
            value_node=value_node,
            parent=parent,
            parent_node_type=parent_node_type,
            class_name=state.class_stack[-1] if state.class_stack else None,
        )
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
        field = node_text(name_node, snapshot.content)
        if not field:
            return
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
        func_name = node_text(name_node, snapshot.content)
        if not func_name:
            return
        parent = state.class_stack[-1]
        _emit_bound_callable(
            name=func_name,
            value_node=value_node,
            parent=parent,
            parent_node_type="type",
            class_name=parent,
        )
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
