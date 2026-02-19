# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Python Tree-sitter analyzer."""

from __future__ import annotations

from .python_analyzer import PythonAnalyzer
from .python_imports import (
    module_name,
    _python_module_name,
    _parse_imports,
    _resolved_python_imports,
    _resolve_python_module_name,
    _package_context,
    _repo_root_from_snapshot,
)

__all__ = [
    "PythonAnalyzer",
    "module_name",
    "_python_module_name",
    "_parse_imports",
    "_resolved_python_imports",
    "_resolve_python_module_name",
    "_package_context",
    "_repo_root_from_snapshot",
]
