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

def _python_inspector_cached(
    root_key: str, relative_path: str
) -> Optional[_PythonInspector]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .profile_introspection_python import _PythonInspector
        return _PythonInspector(source)
    except SyntaxError:
        return None

def _typescript_inspector_cached(
    root_key: str, relative_path: str
) -> Optional[_TypeScriptInspector]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .profile_introspection_typescript import _TypeScriptInspector
        return _TypeScriptInspector(source)
    except SyntaxError:
        return None
