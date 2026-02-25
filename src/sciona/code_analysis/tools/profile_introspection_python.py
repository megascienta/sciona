# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .tree_sitter import build_parser
from .profile_introspection_cache import _python_inspector_cached

@dataclass
class _FunctionDetails:
    parameters: List[str]
    decorators: List[str]

@dataclass
class _ClassDetails:
    decorators: List[str]
    bases: List[str]

class _PythonInspector:
    _PARSER = None

    def __init__(self, source: str) -> None:
        if _PythonInspector._PARSER is None:
            _PythonInspector._PARSER = build_parser("python")
        assert _PythonInspector._PARSER is not None
        self._source = source.encode("utf-8")
        self._tree = _PythonInspector._PARSER.parse(self._source)
        self.functions: Dict[Tuple[int, int], _FunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _ClassDetails] = {}
        self._scan(self._tree.root_node, decorators=())

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_FunctionDetails]:
        return self.functions.get((start_line, end_line))

    def class_details(self, start_line: int, end_line: int) -> Optional[_ClassDetails]:
        return self.classes.get((start_line, end_line))

    def _scan(self, node, *, decorators: tuple[str, ...]) -> None:
        node_type = getattr(node, "type", "")
        if node_type == "decorated_definition":
            decorated = self._decorated_target(node)
            if decorated is None:
                return
            self._scan(decorated, decorators=tuple(self._decorator_names(node)))
            return
        if node_type in {"function_definition", "async_function_definition"}:
            self._record_function(node, decorators=decorators)
        elif node_type == "class_definition":
            self._record_class(node, decorators=decorators)
        for child in getattr(node, "children", []):
            self._scan(child, decorators=())

    def _record_function(self, node, *, decorators: tuple[str, ...]) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        self.functions[(lineno, end_lineno)] = _FunctionDetails(
            parameters=_collect_parameters(params_node, self._source),
            decorators=list(decorators),
        )

    def _record_class(self, node, *, decorators: tuple[str, ...]) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        superclasses_node = node.child_by_field_name("superclasses")
        self.classes[(lineno, end_lineno)] = _ClassDetails(
            decorators=list(decorators),
            bases=_collect_bases(superclasses_node, self._source),
        )

    def _decorated_target(self, node):
        for child in getattr(node, "children", []):
            if child.type in {"function_definition", "async_function_definition", "class_definition"}:
                return child
        return None

    def _decorator_names(self, node) -> list[str]:
        decorators: list[str] = []
        for child in getattr(node, "children", []):
            if child.type != "decorator":
                continue
            text = _node_text(child, self._source).strip()
            if not text:
                continue
            if text.startswith("@"):
                text = text[1:].strip()
            if text:
                decorators.append(text)
        return decorators

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
    return details.parameters, details.decorators

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
    return details.decorators, details.bases

def _python_inspector(
    repo_root: Path, relative_path: str
) -> Optional[_PythonInspector]:
    return _python_inspector_cached(str(repo_root.resolve()), relative_path)

def _collect_parameters(parameters_node, source: bytes) -> List[str]:
    if parameters_node is None:
        return []
    fragment = _node_text(parameters_node, source).strip()
    if not fragment.startswith("(") or not fragment.endswith(")"):
        return []
    inner = fragment[1:-1].strip()
    if not inner:
        return []
    params: List[str] = []
    for entry in _split_comma_aware(inner):
        token = entry.strip()
        if not token or token in {"*", "/"}:
            continue
        token = token.split("=", 1)[0].strip()
        token = token.split(":", 1)[0].strip()
        if not token:
            continue
        if token.startswith("**"):
            value = token[2:].strip()
            if value:
                params.append(f"**{value}")
            continue
        if token.startswith("*"):
            value = token[1:].strip()
            if value:
                params.append(f"*{value}")
            continue
        params.append(token)
    return params

def _collect_bases(superclasses_node, source: bytes) -> List[str]:
    if superclasses_node is None:
        return []
    fragment = _node_text(superclasses_node, source).strip()
    if not fragment.startswith("(") or not fragment.endswith(")"):
        return []
    inner = fragment[1:-1].strip()
    if not inner:
        return []
    return [entry.strip() for entry in _split_comma_aware(inner) if entry.strip()]

def _split_comma_aware(text: str) -> List[str]:
    parts: List[str] = []
    depth = 0
    current: list[str] = []
    for char in text:
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth > 0:
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return parts

def _node_text(node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")
