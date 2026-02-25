# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Inspector cache loaders for profile introspection."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def _python_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
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


def _typescript_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
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


def _java_inspector_cached(root_key: str, relative_path: str) -> Optional[object]:
    path = Path(root_key) / relative_path
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        from .profile_introspection_java import _JavaInspector

        return _JavaInspector(source)
    except SyntaxError:
        return None

