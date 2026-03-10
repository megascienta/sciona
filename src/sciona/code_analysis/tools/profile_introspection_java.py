# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for Java profiling helpers."""

from __future__ import annotations

from ..core.extract.parsing.parser_bootstrap import bootstrap_tree_sitter_parser
from .profiling.java import _JavaInspector, java_class_extras, java_function_extras

_BOOTSTRAP_HELPER_REFERENCE = bootstrap_tree_sitter_parser
# bootstrap_tree_sitter_parser(

__all__ = ["_JavaInspector", "java_class_extras", "java_function_extras"]
