# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .tree_sitter import build_parser
from .profile_introspection_cache import _python_inspector_cached

_MAX_AST_DEPTH = 2000

@dataclass
class _FunctionDetails:
    parameters: List[str]
    decorators: List[str]

@dataclass
class _ClassDetails:
    decorators: List[str]
    bases: List[str]

class _PythonInspector:
    def __init__(self, source: str) -> None:
        self._tree = ast.parse(source)
        self.functions: Dict[Tuple[int, int], _FunctionDetails] = {}
        self.classes: Dict[Tuple[int, int], _ClassDetails] = {}
        self._scan(self._tree, 0)

    def function_details(
        self, start_line: int, end_line: int
    ) -> Optional[_FunctionDetails]:
        return self.functions.get((start_line, end_line))

    def class_details(self, start_line: int, end_line: int) -> Optional[_ClassDetails]:
        return self.classes.get((start_line, end_line))

    def _scan(self, node: ast.AST, depth: int) -> None:
        if depth > _MAX_AST_DEPTH:
            return
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._record_function(child)
            if isinstance(child, ast.ClassDef):
                self._record_class(child)
            self._scan(child, depth + 1)

    def _record_function(self, node: ast.AST) -> None:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is None or end_lineno is None:
            return
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        self.functions[(lineno, end_lineno)] = _FunctionDetails(
            parameters=_collect_parameters(node.args),
            decorators=[
                _safe_unparse(entry) for entry in getattr(node, "decorator_list", [])
            ],
        )

    def _record_class(self, node: ast.ClassDef) -> None:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is None or end_lineno is None:
            return
        bases = [_safe_unparse(entry) for entry in node.bases]
        for keyword in node.keywords:
            expr = _safe_unparse(keyword.value)
            if keyword.arg:
                bases.append(f"{keyword.arg}={expr}")
            else:
                bases.append(expr)
        self.classes[(lineno, end_lineno)] = _ClassDetails(
            decorators=[_safe_unparse(entry) for entry in node.decorator_list],
            bases=bases,
        )

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

def _collect_parameters(args: ast.arguments) -> List[str]:
    params: List[str] = []
    for entry in getattr(args, "posonlyargs", []):
        params.append(entry.arg)
    for entry in args.args:
        params.append(entry.arg)
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    if getattr(args, "kwonlyargs", None):
        for entry in args.kwonlyargs:
            params.append(entry.arg)
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")
    return params

def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node).strip()
    except AttributeError:
        return ast.dump(node)
    except ValueError:
        return ""
