# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .tree_sitter import build_parser
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
            _TypeScriptInspector._PARSER = build_parser("typescript")
        assert _TypeScriptInspector._PARSER is not None
        tree = _TypeScriptInspector._PARSER.parse(source.encode("utf-8"))
        self._source = source
        self.functions: Dict[Tuple[int, int], _TypeScriptFunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _TypeScriptClassDetails] = {}
        self._scan(tree.root_node)

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptFunctionDetails]:
        return self.functions.get((start_line, end_line))

    def class_details(
        self, start_line: int, end_line: int
    ) -> Optional[_TypeScriptClassDetails]:
        return self.classes.get((start_line, end_line))

    def _scan(self, node) -> None:
        node_type = getattr(node, "type", "")
        if node_type in {"function_declaration", "method_definition"}:
            self._record_function(node)
        if node_type == "class_declaration":
            self._record_class(node)
        for child in getattr(node, "children", []):
            self._scan(child)

    def _record_function(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        params_node = node.child_by_field_name("parameters")
        parameters: List[str] = []
        if params_node:
            text = self._slice(params_node.start_byte, params_node.end_byte)
            parameters = _parse_typescript_parameters(text)
        decorators = _collect_ts_decorators(node, self._source)
        self.functions[(lineno, end_lineno)] = _TypeScriptFunctionDetails(
            parameters=parameters, decorators=decorators
        )

    def _record_class(self, node) -> None:
        lineno = node.start_point[0] + 1
        end_lineno = node.end_point[0] + 1
        decorators = _collect_ts_decorators(node, self._source)
        bases: List[str] = []
        heritage = node.child_by_field_name("heritage")
        if heritage:
            text = self._slice(heritage.start_byte, heritage.end_byte)
            bases = _parse_typescript_bases(text)
        self.classes[(lineno, end_lineno)] = _TypeScriptClassDetails(
            decorators=decorators, bases=bases
        )

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

def _parse_typescript_parameters(fragment: str) -> List[str]:
    stripped = fragment.strip()
    if not stripped.startswith("(") or not stripped.endswith(")"):
        return []
    inner = stripped[1:-1].strip()
    if not inner:
        return []
    params: List[str] = []
    for raw in inner.split(","):
        piece = raw.strip()
        if not piece:
            continue
        piece = piece.split("=")[0].strip()
        piece = piece.split(":")[0].strip()
        params.append(piece)
    return params

def _parse_typescript_bases(heritage: str) -> List[str]:
    bases: List[str] = []
    fragments = heritage.replace("implements", ",").replace("extends", ",").split(",")
    for fragment in fragments:
        entry = fragment.strip().strip("{").strip("}")
        if entry:
            bases.append(entry)
    return bases

def _collect_ts_decorators(node, source: str) -> List[str]:
    decorators: List[str] = []
    if not hasattr(node, "children"):
        return decorators
    for child in node.children:
        if child.type == "decorator":
            text = (
                source.encode("utf-8")[child.start_byte : child.end_byte]
                .decode("utf-8")
                .strip()
            )
            decorators.append(text)
    return decorators
