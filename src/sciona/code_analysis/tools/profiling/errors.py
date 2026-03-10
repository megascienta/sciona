# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Exceptions for profile introspection tree-sitter operations."""

from __future__ import annotations


class ProfileIntrospectionError(RuntimeError):
    """Base profile introspection exception."""


class TreeSitterBootstrapError(ProfileIntrospectionError):
    """Raised when tree-sitter parser/bootstrap setup fails."""


class QueryCompileError(ProfileIntrospectionError):
    """Raised when tree-sitter query compilation/execution fails."""


__all__ = [
    "ProfileIntrospectionError",
    "QueryCompileError",
    "TreeSitterBootstrapError",
]
