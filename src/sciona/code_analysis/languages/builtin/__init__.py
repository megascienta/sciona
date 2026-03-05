# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Builtin SCIONA language adapters."""

from .java import JavaAnalyzer, module_name as java_module_name
from .python import PythonAnalyzer, module_name as python_module_name
from .typescript import TypeScriptAnalyzer, module_name as typescript_module_name

__all__ = [
    "JavaAnalyzer",
    "PythonAnalyzer",
    "TypeScriptAnalyzer",
    "java_module_name",
    "python_module_name",
    "typescript_module_name",
]
