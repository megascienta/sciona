# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord
from .query_surface import PYTHON_STRUCTURAL_NODE_TYPES
from .shared import node_text as shared_node_text


@dataclass
class PythonNodeState:
    class_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    class_name_candidates: dict[str, set[str]] = field(default_factory=dict)
    class_body_map: dict[str, object] = field(default_factory=dict)
    pending_calls: list[tuple[str, str, object | None, str | None]] = field(
        default_factory=list
    )


def _node_text(node, content: bytes) -> str | None:
    return shared_node_text(node, content)


def _decorator_names(node, content: bytes) -> tuple[str, ...]:
    decorators: list[str] = []
    for child in getattr(node, "named_children", []):
        if child.type != "decorator":
            continue
        text = _node_text(child, content)
        if text:
            decorators.append(text)
    return tuple(decorators)


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


def walk_python_nodes(
    node,
    *,
    language: str,
    snapshot: FileSnapshot,
    module_name: str,
    result,
    state: PythonNodeState,
    decorators: tuple[str, ...] = (),
) -> None:
    if node.type == "decorated_definition":
        collected_decorators = _decorator_names(node, snapshot.content)
        definition = node.child_by_field_name("definition")
        if definition is None:
            for child in getattr(node, "named_children", []):
                if child.type in {"class_definition", "function_definition", "async_function_definition"}:
                    definition = child
                    break
        if definition is not None:
            walk_python_nodes(
                definition,
                language=language,
                snapshot=snapshot,
                module_name=module_name,
                result=result,
                state=state,
                decorators=collected_decorators,
            )
        return

    if node.type == "class_definition":
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        class_name = _node_text(name_node, snapshot.content)
        if not class_name:
            return
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
                    "kind": "class",
                    "bases": list(_python_bases(node, snapshot.content)),
                    "decorators": list(decorators),
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
        state.class_methods.setdefault(qualified, set())
        state.class_stack.append(qualified)
        body = node.child_by_field_name("body")
        if body is not None:
            state.class_body_map[qualified] = body
        if body:
            for child in _python_structural_children(body):
                walk_python_nodes(
                    child,
                    language=language,
                    snapshot=snapshot,
                    module_name=module_name,
                    result=result,
                    state=state,
                    decorators=(),
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
        if state.class_stack:
            node_type = "method"
            parent = state.class_stack[-1]
            qualified = f"{parent}.{func_name}"
            parent_node_type = "class"
            edge_type = "DEFINES_METHOD"
            state.class_methods.setdefault(parent, set()).add(func_name)
        else:
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
                    {
                        "kind": (
                            "async_function"
                            if _is_async_callable(node, snapshot.content)
                            else "function"
                        ),
                        "decorators": list(decorators),
                    }
                    if decorators or _is_async_callable(node, snapshot.content)
                    else None
                ),
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
        state.pending_calls.append(
            (
                qualified,
                node_type,
                body,
                state.class_stack[-1] if state.class_stack else None,
            )
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
            decorators=(),
        )
