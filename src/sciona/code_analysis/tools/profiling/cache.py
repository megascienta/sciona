# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Inspector cache loaders for profile introspection."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from .errors import QueryCompileError, TreeSitterBootstrapError


def _resolve_safe_profile_path(root_key: str, relative_path: str) -> Path | None:
    candidate = Path(relative_path)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        return None
    root = Path(root_key).resolve()
    path = (root / candidate).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


@lru_cache(maxsize=512)
def _python_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = _resolve_safe_profile_path(root_key, relative_path)
    if path is None:
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .python import _PythonInspector

        return _PythonInspector(source)
    except (TreeSitterBootstrapError, QueryCompileError):
        return None


@lru_cache(maxsize=512)
def _typescript_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = _resolve_safe_profile_path(root_key, relative_path)
    if path is None:
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .typescript import _TypeScriptInspector

        return _TypeScriptInspector(source)
    except (TreeSitterBootstrapError, QueryCompileError):
        return None


@lru_cache(maxsize=512)
def _javascript_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = _resolve_safe_profile_path(root_key, relative_path)
    if path is None:
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .typescript import _TypeScriptInspector
        from .query_surface import (
            JAVASCRIPT_PROFILE_BASE_NODE_TYPES,
            JAVASCRIPT_PROFILE_CLASS_NODE_TYPES,
            JAVASCRIPT_PROFILE_FUNCTION_NODE_TYPES,
            JAVASCRIPT_PROFILE_PARAMETER_NODE_TYPES,
        )

        return _TypeScriptInspector(
            source,
            language_name="javascript",
            function_node_types=JAVASCRIPT_PROFILE_FUNCTION_NODE_TYPES,
            class_node_types=JAVASCRIPT_PROFILE_CLASS_NODE_TYPES,
            parameter_node_types=JAVASCRIPT_PROFILE_PARAMETER_NODE_TYPES,
            base_node_types=JAVASCRIPT_PROFILE_BASE_NODE_TYPES,
        )
    except (TreeSitterBootstrapError, QueryCompileError):
        return None


@lru_cache(maxsize=512)
def _java_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = _resolve_safe_profile_path(root_key, relative_path)
    if path is None:
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .java import _JavaInspector

        return _JavaInspector(source)
    except (TreeSitterBootstrapError, QueryCompileError):
        return None
