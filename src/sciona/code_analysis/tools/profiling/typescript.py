# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from .errors import TreeSitterBootstrapError
from .query import find_profile_nodes_of_types
from .query_surface import (
    JAVASCRIPT_PROFILE_BASE_NODE_TYPES,
    JAVASCRIPT_PROFILE_CLASS_NODE_TYPES,
    JAVASCRIPT_PROFILE_FUNCTION_NODE_TYPES,
    JAVASCRIPT_PROFILE_PARAMETER_NODE_TYPES,
    TYPESCRIPT_PROFILE_BASE_NODE_TYPES,
    TYPESCRIPT_PROFILE_CLASS_NODE_TYPES,
    TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES,
    TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES,
)
from .cache import (
    _javascript_inspector_cached,
    _typescript_inspector_cached,
)

@dataclass
class _TypeScriptFunctionDetails:
    parameters: List[str]

@dataclass
class _TypeScriptClassDetails:
    bases: List[str]

class _TypeScriptInspector:
    _PARSERS: dict[str, object] = {}

    def __init__(
        self,
        source: str,
        *,
        language_name: str = "typescript",
        function_node_types: tuple[str, ...] = TYPESCRIPT_PROFILE_FUNCTION_NODE_TYPES,
        class_node_types: tuple[str, ...] = TYPESCRIPT_PROFILE_CLASS_NODE_TYPES,
        parameter_node_types: tuple[str, ...] = TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES,
        base_node_types: tuple[str, ...] = TYPESCRIPT_PROFILE_BASE_NODE_TYPES,
    ) -> None:
        parser = _TypeScriptInspector._PARSERS.get(language_name)
        if parser is None:
            try:
                parser, _language, _diagnostics = (
                    bootstrap_tree_sitter_parser(language_name)
                )
            except RuntimeError as exc:
                raise TreeSitterBootstrapError(str(exc)) from exc
            _TypeScriptInspector._PARSERS[language_name] = parser
        tree = parser.parse(source.encode("utf-8"))
        self._language_name = language_name
        self._function_node_types = function_node_types
        self._class_node_types = class_node_types
        self._parameter_node_types = parameter_node_types
        self._base_node_types = base_node_types
        self._source = source
        self.functions: Dict[Tuple[int, int], _TypeScriptFunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _TypeScriptClassDetails] = {}
        self._function_span_index: Dict[
            int, List[Tuple[Tuple[int, int], _TypeScriptFunctionDetails]]
        ] = {}
        self._class_span_index: Dict[
            int, List[Tuple[Tuple[int, int], _TypeScriptClassDetails]]
        ] = {}
        self._scan(tree.root_node)
        self._finalize_span_indexes()

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptFunctionDetails]:
        exact = self.functions.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self._function_span_index, start_line, end_line)

    def class_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptClassDetails]:
        exact = self.classes.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self._class_span_index, start_line, end_line)

    def _scan(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type in self._function_node_types:
            self._record_function(node)
        if node_type in self._class_node_types:
            self._record_class(node)
        self._record_expression_callable(node)
        self._record_expression_class(node)
        for child in getattr(node, "children", []):
            self._scan(child)

    def _record_function(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        parameters = _collect_typescript_parameters(
            params_node,
            self._source,
            language_name=self._language_name,
            parameter_node_types=self._parameter_node_types,
        )
        self.functions[(lineno, end_lineno)] = _TypeScriptFunctionDetails(
            parameters=parameters
        )
        self._function_span_index.setdefault(lineno, []).append(
            ((lineno, end_lineno), self.functions[(lineno, end_lineno)])
        )

    def _record_class(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
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
        bases = _collect_typescript_bases(
            heritage,
            self._source,
            language_name=self._language_name,
            base_node_types=self._base_node_types,
        )
        self.classes[(lineno, end_lineno)] = _TypeScriptClassDetails(
            bases=bases
        )
        self._class_span_index.setdefault(lineno, []).append(
            ((lineno, end_lineno), self.classes[(lineno, end_lineno)])
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
        lineno = value_node.start_point[0] + 1
        end_lineno = value_node.end_point[0] + 1
        self.classes[(lineno, end_lineno)] = _TypeScriptClassDetails(bases=[])

    def _slice(self, start: int, end: int) -> str:
        return self._source.encode("utf-8")[start:end].decode("utf-8")

    def _finalize_span_indexes(self) -> None:
        for entries in self._function_span_index.values():
            entries.sort(key=lambda item: item[0][1])
        for entries in self._class_span_index.values():
            entries.sort(key=lambda item: item[0][1])

def typescript_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> List[str]:
    """Return parameter names for TypeScript functions."""
    if language != "typescript" or repo_root is None:
        return []
    inspector = _typescript_inspector(repo_root, file_path)
    parameters: List[str] = []
    if inspector:
        details = inspector.function_details(start_line, end_line)
        if details:
            parameters = details.parameters
    return parameters

def typescript_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> List[str]:
    """Return base clauses for TypeScript classes."""
    if language != "typescript" or repo_root is None:
        return []
    inspector = _typescript_inspector(repo_root, file_path)
    if not inspector:
        return []
    details = inspector.class_details(start_line, end_line)
    if not details:
        return []
    return details.bases

def javascript_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> List[str]:
    """Return parameter names for JavaScript functions."""
    if language != "javascript" or repo_root is None:
        return []
    inspector = _javascript_inspector(repo_root, file_path)
    parameters: List[str] = []
    if inspector:
        details = inspector.function_details(start_line, end_line)
        if details:
            parameters = details.parameters
    return parameters

def javascript_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> List[str]:
    """Return base clauses for JavaScript classes."""
    if language != "javascript" or repo_root is None:
        return []
    inspector = _javascript_inspector(repo_root, file_path)
    if not inspector:
        return []
    details = inspector.class_details(start_line, end_line)
    if not details:
        return []
    return details.bases

def _typescript_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_TypeScriptInspector]:
    return _typescript_inspector_cached(str(repo_root.resolve()), relative_path)

def _javascript_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_TypeScriptInspector]:
    return _javascript_inspector_cached(str(repo_root.resolve()), relative_path)

def _collect_typescript_parameters(
    parameters_node,
    source: str,
    *,
    language_name: str = "typescript",
    parameter_node_types: tuple[str, ...] = TYPESCRIPT_PROFILE_PARAMETER_NODE_TYPES,
) -> List[str]:
    if parameters_node is None:
        return []
    source_bytes = source.encode("utf-8")
    params: List[str] = []
    for child in find_profile_nodes_of_types(
        parameters_node,
        language_name=language_name,
        node_types=parameter_node_types,
    ):
        if not _is_direct_child(child, parameters_node):
            continue
        name = child.child_by_field_name("pattern") or child.child_by_field_name("name")
        if name is None and child.type == "identifier":
            name = child
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

def _collect_typescript_bases(
    heritage_node,
    source: str,
    *,
    language_name: str = "typescript",
    base_node_types: tuple[str, ...] = TYPESCRIPT_PROFILE_BASE_NODE_TYPES,
) -> List[str]:
    if heritage_node is None:
        return []
    source_bytes = source.encode("utf-8")
    bases: List[str] = []
    for child in find_profile_nodes_of_types(
        heritage_node,
        language_name=language_name,
        node_types=base_node_types,
    ):
        value = source_bytes[child.start_byte : child.end_byte].decode("utf-8").strip()
        if value and value not in {"extends", "implements"}:
            bases.append(value)
    return list(dict.fromkeys(bases))

def _is_direct_child(node, parent) -> bool:
    owner = getattr(node, "parent", None)
    if owner is None:
        return False
    return (
        owner.type == getattr(parent, "type", None)
        and owner.start_byte == getattr(parent, "start_byte", -1)
        and owner.end_byte == getattr(parent, "end_byte", -1)
    )


def _fuzzy_span_lookup(span_index, start_line: int, end_line: int):
    if not span_index:
        return None
    candidates = list(span_index.get(start_line, ()))
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            0 if item[0][1] >= end_line else 1,
            abs(item[0][1] - end_line),
            item[0][1],
        )
    )
    return candidates[0][1]
