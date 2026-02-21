# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python node extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ...normalize.model import EdgeRecord, FileSnapshot, SemanticNodeRecord


@dataclass
class PythonNodeState:
    class_stack: List[str] = field(default_factory=list)
    module_functions: set[str] = field(default_factory=set)
    class_methods: dict[str, set[str]] = field(default_factory=dict)
    class_name_map: dict[str, str] = field(default_factory=dict)
    pending_calls: list[tuple[str, str, object | None, str | None]] = field(
        default_factory=list
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
    if node.type == "class_definition":
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
        state.class_methods.setdefault(qualified, set())
        state.class_stack.append(qualified)
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
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

    if node.type == "function_definition":
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        func_name = snapshot.content[name_node.start_byte : name_node.end_byte].decode(
            "utf-8"
        )
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

    for child in getattr(node, "children", []):
        walk_python_nodes(
            child,
            language=language,
            snapshot=snapshot,
            module_name=module_name,
            result=result,
            state=state,
        )
