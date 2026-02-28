# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.extract.utils import bootstrap_tree_sitter_parser
from .profile_errors import TreeSitterBootstrapError
from .profile_query import find_profile_nodes_of_types
from .profile_query_surface import (
    TYPESCRIPT_PROFILE_BASE_NODE_TYPES,
    TYPESCRIPT_PROFILE_CLASS_NODE_TYPES,
    TYPESCRIPT_PROFILE_DECORATOR_NODE_TYPES,
    TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES,
    TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES,
)
from .profile_introspection_cache import _typescript_inspector_cached

@dataclass
class _TypeScriptFunctionDetails:
    parameters: List[str]
    decorators: List[str]

@dataclass
class _TypeScriptClassDetails:
    decorators: List[str]
    bases: List[str]

class _TypeScriptInspector:
    _PARSER = None

    def __init__(self, source: str) -> None:
        if _TypeScriptInspector._PARSER is None:
            try:
                _TypeScriptInspector._PARSER, _language, _diagnostics = (
                    bootstrap_tree_sitter_parser("typescript")
                )
            except RuntimeError as exc:
                raise TreeSitterBootstrapError(str(exc)) from exc
        assert _TypeScriptInspector._PARSER is not None
        tree = _TypeScriptInspector._PARSER.parse(source.encode("utf-8"))
        self._source = source
        self.functions: Dict[Tuple[int, int], _TypeScriptFunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _TypeScriptClassDetails] = {}
        self._scan(tree.root_node)

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptFunctionDetails]:
        exact = self.functions.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self.functions, start_line, end_line)

    def class_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptClassDetails]:
        exact = self.classes.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self.classes, start_line, end_line)

    def _scan(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type in TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES:
            self._record_function(node)
        if node_type in TYPESCRIPT_PROFILE_CLASS_NODE_TYPES:
            self._record_class(node)
        self._record_expression_callable(node)
        self._record_expression_class(node)
        for child in getattr(node, "children", []):
            self._scan(child)

    def _record_function(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        parameters = _collect_typescript_parameters(params_node, self._source)
        decorators = _collect_ts_decorators(node, self._source)
        self.functions[(lineno, end_lineno)] = _TypeScriptFunctionDetails(
            parameters=parameters, decorators=decorators
        )

    def _record_class(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        decorators = _collect_ts_decorators(node, self._source)
        heritage = node.child_by_field_name("heritage")
        bases = _collect_typescript_bases(heritage, self._source)
        self.classes[(lineno, end_lineno)] = _TypeScriptClassDetails(
            decorators=decorators, bases=bases
        )

    def _record_expression_callable(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type == "variable_declarator":
            value_node = node.child_by_field_name("value") or node.child_by_field_name(
                "initializer"
            )
            if value_node is not None and value_node.type in {
                "arrow_function",
                "function",
                "function_expression",
            }:
                self._record_function(value_node)
            return
        if node_type not in {
            "public_field_definition",
            "private_field_definition",
            "property_definition",
            "field_definition",
        }:
            return
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if value_node is not None and value_node.type in {
            "arrow_function",
            "function",
            "function_expression",
        }:
            self._record_function(value_node)

    def _record_expression_class(self, node) -> None:
        if getattr(node, "type", "") != "variable_declarator":
            return
        value_node = node.child_by_field_name("value") or node.child_by_field_name(
            "initializer"
        )
        if value_node is None or value_node.type not in {"class", "class_expression"}:
            return
        self._record_class(value_node)

    def _slice(self, start: int, end: int) -> str:
        return self._source.encode("utf-8")[start:end].decode("utf-8")

def typescript_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    """Return parameter names and decorators for TypeScript functions."""
    if language != "typescript" or repo_root is None:
        return [], []
    inspector = _typescript_inspector(repo_root, file_path)
    parameters: List[str] = []
    decorators: List[str] = []
    if inspector:
        details = inspector.function_details(start_line, end_line)
        if details:
            parameters = details.parameters
            decorators = details.decorators
    return parameters, decorators

def typescript_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    """Return decorators + base clauses for TypeScript classes."""
    if language != "typescript" or repo_root is None:
        return [], []
    inspector = _typescript_inspector(repo_root, file_path)
    if not inspector:
        return [], []
    details = inspector.class_details(start_line, end_line)
    if not details:
        return [], []
    return details.decorators, details.bases

def _typescript_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_TypeScriptInspector]:
    return _typescript_inspector_cached(str(repo_root.resolve()), relative_path)

def _collect_typescript_parameters(parameters_node, source: str) -> List[str]:
    if parameters_node is None:
        return []
    source_bytes = source.encode("utf-8")
    params: List[str] = []
    for child in find_profile_nodes_of_types(
        parameters_node,
        language_name="typescript",
        node_types=TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES,
    ):
        if not _is_direct_child(child, parameters_node):
            continue
        name = child.child_by_field_name("pattern") or child.child_by_field_name("name")
        if name is None:
            name = next(
                (entry for entry in getattr(child, "children", []) if entry.type == "identifier"),
                None,
            )
        if name is None:
            continue
        value = source_bytes[name.start_byte : name.end_byte].decode("utf-8").strip()
        if not value:
            continue
        raw = source_bytes[child.start_byte : child.end_byte].decode("utf-8").strip()
        if raw.startswith("...") and not value.startswith("..."):
            value = f"...{value}"
        params.append(value)
    return params

def _collect_typescript_bases(heritage_node, source: str) -> List[str]:
    if heritage_node is None:
        return []
    source_bytes = source.encode("utf-8")
    bases: List[str] = []
    for child in find_profile_nodes_of_types(
        heritage_node,
        language_name="typescript",
        node_types=TYPESCRIPT_PROFILE_BASE_NODE_TYPES,
    ):
        value = source_bytes[child.start_byte : child.end_byte].decode("utf-8").strip()
        if value and value not in {"extends", "implements"}:
            bases.append(value)
    return list(dict.fromkeys(bases))

def _collect_ts_decorators(node, source: str) -> List[str]:
    decorators: List[str] = []
    for child in find_profile_nodes_of_types(
        node,
        language_name="typescript",
        node_types=TYPESCRIPT_PROFILE_DECORATOR_NODE_TYPES,
    ):
        text = (
            source.encode("utf-8")[child.start_byte : child.end_byte]
            .decode("utf-8")
            .strip()
        )
        if text:
            decorators.append(text)
    return decorators


def _is_direct_child(node, parent) -> bool:
    owner = getattr(node, "parent", None)
    if owner is None:
        return False
    return (
        owner.type == getattr(parent, "type", None)
        and owner.start_byte == getattr(parent, "start_byte", -1)
        and owner.end_byte == getattr(parent, "end_byte", -1)
    )


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
