# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ....core.normalize_model import EdgeRecord, FileSnapshot, SemanticNodeRecord
from ...common.naming.lexical_naming import LexicalNameDisambiguator
from ...common.query.query_surface import (
    PYTHON_STRUCTURAL_CARRIER_NODE_TYPES,
    PYTHON_STRUCTURAL_NODE_TYPES,
)
from ...common.support.shared import node_text as shared_node_text


@dataclass
class PythonNodeState:
    class_stack: List[str] = field(default_factory=list)
    callable_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    class_name_candidates: dict[str, set[str]] = field(default_factory=dict)
    class_body_map: dict[str, object] = field(default_factory=dict)
    pending_calls: list[tuple[str, str, object | None, str | None]] = field(
        default_factory=list
    )
    name_disambiguator: LexicalNameDisambiguator = field(
        default_factory=LexicalNameDisambiguator
    )


def _node_text(node, content: bytes) -> str | None:
    return shared_node_text(node, content)


def _python_bases(node, content: bytes) -> tuple[str, ...]:
    superclasses = node.child_by_field_name("superclasses")
    if superclasses is None:
        return ()
    bases: list[str] = []
    for child in getattr(superclasses, "named_children", []):
        text = _node_text(child, content)
        if text:
            bases.append(text)
    return tuple(bases)


def _is_async_callable(node, content: bytes) -> bool:
    if node.type == "async_function_definition":
        return True
    text = (_node_text(node, content) or "").lstrip()
    return text.startswith("async ")


def _python_structural_children(node) -> list[object]:
    return [
        child
        for child in getattr(node, "named_children", [])
        if getattr(child, "type", "") in PYTHON_STRUCTURAL_NODE_TYPES
    ]


def _python_structural_children_from_body(node) -> list[object]:
    children: list[object] = []
    for child in getattr(node, "named_children", []):
        child_type = getattr(child, "type", "")
        if child_type in PYTHON_STRUCTURAL_NODE_TYPES:
            children.append(child)
            continue
        if child_type not in PYTHON_STRUCTURAL_CARRIER_NODE_TYPES:
            continue
        children.extend(_python_structural_children(child))
    return children


def _lambda_body(node):
    if node is None:
        return None
    return node.child_by_field_name("body")


def _disambiguate_child_name(
    *,
    state: PythonNodeState,
    parent: str,
    child_kind: str,
    local_name: str,
) -> str:
    return state.name_disambiguator.canonical_name(
        parent=parent,
        child_kind=child_kind,
        local_name=local_name,
    )


def walk_python_nodes(
    node,
    *,
    language: str,
    snapshot: FileSnapshot,
    module_name: str,
    result,
    state: PythonNodeState,
) -> None:
    if node.type == "expression_statement":
        for child in _python_structural_children(node):
            walk_python_nodes(
                child,
                language=language,
                snapshot=snapshot,
                module_name=module_name,
                result=result,
                state=state,
            )
        return

    if node.type == "decorated_definition":
        definition = node.child_by_field_name("definition")
        if definition is not None:
            walk_python_nodes(
                definition,
                language=language,
                snapshot=snapshot,
                module_name=module_name,
                result=result,
                state=state,
            )
        return

    if node.type == "class_definition":
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = _node_text(name_node, snapshot.content)
        if not class_name:
            return
        if state.callable_stack:
            parent = state.callable_stack[-1]
            parent_node_type = "callable"
        elif state.class_stack:
            parent = state.class_stack[-1]
            parent_node_type = "classifier"
        else:
            parent = module_name
            parent_node_type = "module"
        emitted_name = _disambiguate_child_name(
            state=state,
            parent=parent,
            child_kind="classifier",
            local_name=class_name,
        )
        qualified = f"{parent}.{emitted_name}"
        result.nodes.append(
            SemanticNodeRecord(
                language=language,
                node_type="classifier",
                qualified_name=qualified,
                display_name=class_name,
                file_path=snapshot.record.relative_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                start_byte=node.start_byte,
                end_byte=node.end_byte,
                metadata={
                    "kind": "class",
                    "bases": list(_python_bases(node, snapshot.content)),
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
                dst_node_type="classifier",
                dst_qualified_name=qualified,
                edge_type="LEXICALLY_CONTAINS",
            )
        )
        state.class_methods.setdefault(qualified, set())
        state.class_stack.append(qualified)
        body = node.child_by_field_name("body")
        if body is not None:
            state.class_body_map[qualified] = body
        if body:
            for child in _python_structural_children_from_body(body):
                walk_python_nodes(
                    child,
                    language=language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                )
        state.class_stack.pop()
        return

    if node.type in {"function_definition", "async_function_definition"}:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        func_name = _node_text(name_node, snapshot.content)
        if not func_name:
            return
        current_class = state.class_stack[-1] if state.class_stack else None
        class_body = state.class_body_map.get(current_class) if current_class else None
        parent_node = getattr(node, "parent", None)
        in_class_body = (
            class_body is not None
            and parent_node is not None
            and getattr(parent_node, "start_byte", None) == getattr(class_body, "start_byte", None)
            and getattr(parent_node, "end_byte", None) == getattr(class_body, "end_byte", None)
            and getattr(parent_node, "type", None) == getattr(class_body, "type", None)
        )
        if state.callable_stack and not in_class_body:
            node_type = "callable"
            parent = state.callable_stack[-1]
            parent_node_type = "callable"
            edge_type = "LEXICALLY_CONTAINS"
            role = "nested"
        elif current_class is not None:
            node_type = "callable"
            parent = current_class
            parent_node_type = "classifier"
            edge_type = "LEXICALLY_CONTAINS"
            state.class_methods.setdefault(parent, set()).add(func_name)
            role = "constructor" if func_name == "__init__" else "declared"
        else:
            node_type = "callable"
            parent = module_name
            parent_node_type = "module"
            edge_type = "LEXICALLY_CONTAINS"
            state.module_functions.add(func_name)
            role = "declared"
        emitted_name = _disambiguate_child_name(
            state=state,
            parent=parent,
            child_kind="callable",
            local_name=func_name,
        )
        qualified = f"{parent}.{emitted_name}"
        is_async = _is_async_callable(node, snapshot.content)
        metadata = {"callable_role": role}
        if is_async:
            metadata["kind"] = "async_function"
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
        body = node.child_by_field_name("body")
        state.callable_stack.append(qualified)
        if body:
            for child in _python_structural_children_from_body(body):
                walk_python_nodes(
                    child,
                    language=language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                )
        state.callable_stack.pop()
        state.pending_calls.append(
            (
                qualified,
                node_type,
                body,
                state.class_stack[-1] if state.class_stack else None,
            )
        )
        return

    if node.type in {"assignment", "augmented_assignment"}:
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if (
            left is not None
            and right is not None
            and getattr(left, "type", "") == "identifier"
            and getattr(right, "type", "") == "lambda"
        ):
            func_name = _node_text(left, snapshot.content)
            if func_name:
                if state.callable_stack:
                    parent = state.callable_stack[-1]
                    parent_node_type = "callable"
                    role = "bound"
                elif state.class_stack:
                    parent = state.class_stack[-1]
                    parent_node_type = "classifier"
                    role = "bound"
                else:
                    parent = module_name
                    parent_node_type = "module"
                    role = "bound"
                emitted_name = _disambiguate_child_name(
                    state=state,
                    parent=parent,
                    child_kind="callable",
                    local_name=func_name,
                )
                qualified = f"{parent}.{emitted_name}"
                result.nodes.append(
                    SemanticNodeRecord(
                        language=language,
                        node_type="callable",
                        qualified_name=qualified,
                        display_name=func_name,
                        file_path=snapshot.record.relative_path,
                        start_line=right.start_point[0] + 1,
                        end_line=right.end_point[0] + 1,
                        start_byte=right.start_byte,
                        end_byte=right.end_byte,
                        metadata={"callable_role": role},
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
                if parent_node_type == "module":
                    state.module_functions.add(func_name)
                state.pending_calls.append(
                    (
                        qualified,
                        "callable",
                        _lambda_body(right),
                        state.class_stack[-1] if state.class_stack else None,
                    )
                )
        # Assignment nodes are query-surface carriers; recurse explicitly into
        # structural children only and do not emit assignment as a structural node.
        for child in _python_structural_children(node):
            walk_python_nodes(
                child,
                language=language,
                snapshot=snapshot,
                module_name=module_name,
                result=result,
                state=state,
            )
        return

    for child in _python_structural_children(node):
        walk_python_nodes(
            child,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
        )
