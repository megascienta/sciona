# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for Python profiling helpers."""

from __future__ import annotations

from ..core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from .profiling.python import (
    _ClassDetails,
    _FunctionDetails,
    _PythonInspector,
    _collect_bases,
    _collect_parameters,
    _node_text,
    _python_inspector,
    python_class_extras,
    python_function_extras,
)

_BOOTSTRAP_HELPER_REFERENCE = bootstrap_tree_sitter_parser
# bootstrap_tree_sitter_parser(

__all__ = [
    "_ClassDetails",
    "_FunctionDetails",
    "_PythonInspector",
    "_collect_bases",
    "_collect_parameters",
    "_node_text",
    "_python_inspector",
    "python_class_extras",
    "python_function_extras",
]
