# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Language-specific symbol introspection helpers for profile reducers."""

from __future__ import annotations

from .profile_introspection_python import (
    _ClassDetails,
    _FunctionDetails,
    _PythonInspector,
    _collect_parameters,
    _collect_bases,
    _python_inspector,
    _split_comma_aware,
    _node_text,
    python_class_extras,
    python_function_extras,
)
from .profile_introspection_typescript import (
    _TypeScriptClassDetails,
    _TypeScriptFunctionDetails,
    _TypeScriptInspector,
    _collect_ts_decorators,
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
