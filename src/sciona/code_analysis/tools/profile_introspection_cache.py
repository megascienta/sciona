# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Inspector cache loaders for profile introspection."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from .profile_errors import QueryCompileError, TreeSitterBootstrapError


@lru_cache(maxsize=512)
def _python_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .profile_introspection_python import _PythonInspector

        return _PythonInspector(source)
    except (TreeSitterBootstrapError, QueryCompileError):
        return None


@lru_cache(maxsize=512)
def _typescript_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .profile_introspection_typescript import _TypeScriptInspector

        return _TypeScriptInspector(source)
    except (TreeSitterBootstrapError, QueryCompileError):
        return None


@lru_cache(maxsize=512)
def _java_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .profile_introspection_java import _JavaInspector

        return _JavaInspector(source)
    except (TreeSitterBootstrapError, QueryCompileError):
        return None
