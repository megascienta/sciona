# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.extract.parser_bootstrap import bootstrap_tree_sitter_parser
from .profile_errors import TreeSitterBootstrapError
from .profile_query import find_profile_nodes_of_types
from .profile_query_surface import (
    PYTHON_PROFILE_BASE_NODE_TYPES,
    PYTHON_PROFILE_PARAMETER_NODE_TYPES,
)
from .profile_introspection_cache import _python_inspector_cached

@dataclass
class _FunctionDetails:
    parameters: List[str]

@dataclass
class _ClassDetails:
    bases: List[str]

class _PythonInspector:
    _PARSER = None

    def __init__(self, source: str) -> None:
        if _PythonInspector._PARSER is None:
            try:
                _PythonInspector._PARSER, _language, _diagnostics = (
                    bootstrap_tree_sitter_parser("python")
                )
            except RuntimeError as exc:
                raise TreeSitterBootstrapError(str(exc)) from exc
        assert _PythonInspector._PARSER is not None
        self._source = source.encode("utf-8")
        self._tree = _PythonInspector._PARSER.parse(self._source)
        self.functions: Dict[Tuple[int, int], _FunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _ClassDetails] = {}
        self._scan(self._tree.root_node)

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_FunctionDetails]:
        exact = self.functions.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self.functions, start_line, end_line)

    def class_details(self, start_line: int, end_line: int) -> Optional[_ClassDetails]:
        exact = self.classes.get((start_line, end_line))
        if exact is not None:
            return exact
        return _fuzzy_span_lookup(self.classes, start_line, end_line)

    def _scan(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type == "decorated_definition":
            decorated = self._decorated_target(node)
            if decorated is None:
                return
            self._scan(decorated)
            return
        if node_type in {"function_definition", "async_function_definition"}:
            self._record_function(node)
        elif node_type == "class_definition":
            self._record_class(node)
        for child in getattr(node, "children", []):
            self._scan(child)

    def _record_function(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        self.functions[(lineno, end_lineno)] = _FunctionDetails(
            parameters=_collect_parameters(params_node, self._source),
        )

    def _record_class(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        superclasses_node = node.child_by_field_name("superclasses")
        self.classes[(lineno, end_lineno)] = _ClassDetails(
            bases=_collect_bases(superclasses_node, self._source),
        )

    def _decorated_target(self, node):
        for child in getattr(node, "children", []):
            if child.type in {"function_definition", "async_function_definition", "class_definition"}:
                return child
        return None

def python_function_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    """Return parameters and decorators for Python functions."""
    if language != "python" or repo_root is None:
        return [], []
    inspector = _python_inspector(repo_root, file_path)
    if not inspector:
        return [], []
    details = inspector.function_details(start_line, end_line)
    if not details:
        return [], []
    return details.parameters, []

def python_class_extras(
    language: str,
    repo_root: Optional[Path],
    file_path: str,
    start_line: int,
    end_line: int,
) -> Tuple[List[str], List[str]]:
    """Return decorator/base metadata for Python classes."""
    if language != "python" or repo_root is None:
        return [], []
    inspector = _python_inspector(repo_root, file_path)
    if not inspector:
        return [], []
    details = inspector.class_details(start_line, end_line)
    if not details:
        return [], []
    return [], details.bases

def _python_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_PythonInspector]:
    return _python_inspector_cached(str(repo_root.resolve()), relative_path)

def _collect_parameters(parameters_node, source: bytes) -> List[str]:
    if parameters_node is None:
        return []
    params: List[str] = []
    for child in find_profile_nodes_of_types(
        parameters_node,
        language_name="python",
        node_types=PYTHON_PROFILE_PARAMETER_NODE_TYPES,
    ):
        if not _is_direct_child(child, parameters_node):
            continue
        value = _python_parameter_name(child, source)
        if value:
            params.append(value)
    return params

def _collect_bases(superclasses_node, source: bytes) -> List[str]:
    if superclasses_node is None:
        return []
    bases: list[str] = []
    for child in find_profile_nodes_of_types(
        superclasses_node,
        language_name="python",
        node_types=PYTHON_PROFILE_BASE_NODE_TYPES,
    ):
        value = _node_text(child, source).strip()
        if not value:
            continue
        if value in {"(", ")", ","}:
            continue
        bases.append(value)
    # Preserve stable order and remove duplicates.
    return list(dict.fromkeys(bases))

def _node_text(node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _python_parameter_name(node, source: bytes) -> str | None:
    node_type = getattr(node, "type", "")
    if node_type == "identifier":
        value = _node_text(node, source).strip()
        return value or None
    if node_type in {"default_parameter", "typed_parameter", "typed_default_parameter"}:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            name_node = node.child_by_field_name("pattern")
        if name_node is not None:
            value = _node_text(name_node, source).strip()
            return value or None
    if node_type in {"list_splat_pattern", "dictionary_splat_pattern"}:
        inner = next(
            (child for child in getattr(node, "children", []) if child.type == "identifier"),
            None,
        )
        if inner is None:
            value = _node_text(node, source).strip()
            if not value:
                return None
            if value.startswith("**"):
                return value
            if value.startswith("*"):
                return value
            return f"*{value}"
        prefix = "**" if node_type == "dictionary_splat_pattern" else "*"
        value = _node_text(inner, source).strip()
        return f"{prefix}{value}" if value else None
    return None


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
    candidates = [(span, value) for span, value in mapping.items() if span[0] == start_line]
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
