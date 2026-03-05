# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Builtin SCIONA language adapters."""

from .javascript.javascript import (
    JavaScriptAnalyzer,
    module_name as javascript_module_name,
)
from .java.java import JavaAnalyzer, module_name as java_module_name
from .python.python import PythonAnalyzer, module_name as python_module_name
from .typescript.typescript import TypeScriptAnalyzer, module_name as typescript_module_name

__all__ = [
    "JavaScriptAnalyzer",
    "JavaAnalyzer",
    "PythonAnalyzer",
    "TypeScriptAnalyzer",
    "javascript_module_name",
    "java_module_name",
    "python_module_name",
    "typescript_module_name",
]
