# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for TypeScript and JavaScript profiling helpers."""

from __future__ import annotations

from ..core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from .profiling.typescript import (
    _TypeScriptClassDetails,
    _TypeScriptFunctionDetails,
    _TypeScriptInspector,
    _collect_typescript_bases,
    _collect_typescript_parameters,
    _fuzzy_span_lookup,
    _typescript_inspector,
    javascript_class_extras,
    javascript_function_extras,
    typescript_class_extras,
    typescript_function_extras,
)

_BOOTSTRAP_HELPER_REFERENCE = bootstrap_tree_sitter_parser
# bootstrap_tree_sitter_parser(

__all__ = [
    "_TypeScriptClassDetails",
    "_TypeScriptFunctionDetails",
    "_TypeScriptInspector",
    "_collect_typescript_bases",
    "_collect_typescript_parameters",
    "_fuzzy_span_lookup",
    "_typescript_inspector",
    "javascript_class_extras",
    "javascript_function_extras",
    "typescript_class_extras",
    "typescript_function_extras",
]
