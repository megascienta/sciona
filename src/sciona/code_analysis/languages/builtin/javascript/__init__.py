# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Builtin JavaScript language adapter package."""

from .javascript import JavaScriptAnalyzer, module_name

__all__ = ["JavaScriptAnalyzer", "module_name"]
