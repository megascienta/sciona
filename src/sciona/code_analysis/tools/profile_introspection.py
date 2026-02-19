# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from .profile_introspection_python import (
    _ClassDetails,
    _FunctionDetails,
    _PythonInspector,
    _collect_parameters,
    _python_inspector,
    _safe_unparse,
    _MAX_AST_DEPTH,
    python_class_extras,
    python_function_extras,
)
from .profile_introspection_typescript import (
    _TypeScriptClassDetails,
    _TypeScriptFunctionDetails,
    _TypeScriptInspector,
    _collect_ts_decorators,
    _find_parameter_fragment,
    _line_based_ts_parameters,
    _parse_typescript_bases,
    _parse_typescript_parameters,
    _typescript_inspector,
    typescript_class_extras,
    typescript_function_extras,
)
from .profile_introspection_cache import (
    _python_inspector_cached,
    _typescript_inspector_cached,
)

__all__ = [
    "python_class_extras",
    "python_function_extras",
    "typescript_class_extras",
    "typescript_function_extras",
]
