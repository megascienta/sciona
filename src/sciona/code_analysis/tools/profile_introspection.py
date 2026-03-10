# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for profiling introspection helpers."""

from __future__ import annotations

from .profiling import (
    javascript_class_extras,
    javascript_function_extras,
    java_class_extras,
    java_function_extras,
    python_class_extras,
    python_function_extras,
    typescript_class_extras,
    typescript_function_extras,
)

__all__ = [
    "python_class_extras",
    "python_function_extras",
    "java_class_extras",
    "java_function_extras",
    "typescript_class_extras",
    "typescript_function_extras",
    "javascript_class_extras",
    "javascript_function_extras",
]
