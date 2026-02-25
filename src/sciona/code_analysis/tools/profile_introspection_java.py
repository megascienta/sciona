# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Java symbol introspection helpers for profile reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .profile_introspection_cache import _java_inspector_cached
from .profile_query import find_profile_nodes_of_types
from .profile_query_surface import (
    JAVA_PROFILE_BASE_NODE_TYPES,
    JAVA_PROFILE_CLASS_NODE_TYPES,
    JAVA_PROFILE_FUNCTION_NODE_TYPES,
    JAVA_PROFILE_PARAMETER_NODE_TYPES,
)
from .tree_sitter import build_parser


@dataclass
class _JavaFunctionDetails:
    parameters: List[str]
    decorators: List[str]


@dataclass
class _JavaClassDetails:
    decorators: List[str]
    bases: List[str]


class _JavaInspector:
    _PARSER = None

    def __init__(self, source: str) -> None:
        if _JavaInspector._PARSER is None:
            _JavaInspector._PARSER = build_parser("java")
        assert _JavaInspector._PARSER is not None
        self._source = source.encode("utf-8")
        tree = _JavaInspector._PARSER.parse(self._source)
        self.functions: Dict[Tuple[int, int], _JavaFunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _JavaClassDetails] = {}
        self._scan(tree.root_node)

    def function_details(self, start_line: int, end_line: int) -> Optional[_JavaFunctionDetails]:
        exact = self.functions.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self.functions, start_line, end_line)

    def class_details(self, start_line: int, end_line: int) -> Optional[_JavaClassDetails]:
        exact = self.classes.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self.classes, start_line, end_line)

    def _scan(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type in JAVA_PROFILE_FUNCTION_NODE_TYPES:
            self._record_function(node)
        if node_type in JAVA_PROFILE_CLASS_NODE_TYPES:
            self._record_class(node)
        for child in getattr(node, "children", []):
            self._scan(child)

    def _record_function(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        self.functions[(lineno, end_lineno)] = _JavaFunctionDetails(
            parameters=_collect_java_parameters(params_node, self._source),
            decorators=[],
        )

    def _record_class(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        bases = _collect_java_bases(node, self._source)
        self.classes[(lineno, end_lineno)] = _JavaClassDetails(decorators=[], bases=bases)


def java_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    if language != "java" or repo_root is None:
        return [], []
    inspector = _java_inspector(repo_root, file_path)
    if not inspector:
        return [], []
    details = inspector.function_details(start_line, end_line)
    if not details:
        return [], []
    return details.parameters, details.decorators


def java_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    if language != "java" or repo_root is None:
        return [], []
    inspector = _java_inspector(repo_root, file_path)
    if not inspector:
        return [], []
    details = inspector.class_details(start_line, end_line)
    if not details:
        return [], []
    return details.decorators, details.bases


def _java_inspector(repo_root: Path, relative_path: str) -> Optional[_JavaInspector]:
    return _java_inspector_cached(str(repo_root.resolve()), relative_path)


def _collect_java_parameters(parameters_node, source: bytes) -> List[str]:
    if parameters_node is None:
        return []
    params: list[str] = []
    for child in find_profile_nodes_of_types(
        parameters_node,
        language_name="java",
        node_types=JAVA_PROFILE_PARAMETER_NODE_TYPES,
    ):
        name_node = child.child_by_field_name("name")
        if name_node is None:
            name_node = next(
                (entry for entry in getattr(child, "children", []) if entry.type == "identifier"),
                None,
            )
        if name_node is None:
            continue
        name = source[name_node.start_byte : name_node.end_byte].decode("utf-8").strip()
        if name:
            params.append(name)
    return params


def _collect_java_bases(class_node, source: bytes) -> List[str]:
    base_nodes: list[object] = []
    extends_node = class_node.child_by_field_name("superclass")
    if extends_node is not None:
        base_nodes.extend(
            find_profile_nodes_of_types(
                extends_node,
                language_name="java",
                node_types=JAVA_PROFILE_BASE_NODE_TYPES,
            )
        )
    interfaces_node = class_node.child_by_field_name("interfaces")
    if interfaces_node is not None:
        base_nodes.extend(
            find_profile_nodes_of_types(
                interfaces_node,
                language_name="java",
                node_types=JAVA_PROFILE_BASE_NODE_TYPES,
            )
        )
    bases: list[str] = []
    for node in base_nodes:
        value = source[node.start_byte : node.end_byte].decode("utf-8").strip()
        if value:
            bases.append(value)
    return list(dict.fromkeys(bases))


def _fuzzy_span_lookup(mapping, start_line: int, end_line: int):
    if not mapping:
        return None
    candidates = [
        (span, value)
        for span, value in mapping.items()
        if span[0] == start_line and span[1] >= end_line
    ]
    if not candidates:
        candidates = [(span, value) for span, value in mapping.items() if span[0] == start_line]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0][1])
    return candidates[0][1]
