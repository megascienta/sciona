# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility shim for module_overview reducer."""

from __future__ import annotations

from ..module_overview import (
    REDUCER_META,
    _language_breakdown,
    _list_children,
    _list_imports,
    _list_methods,
    _list_module_files,
    _module_file_entries,
    _resolve_module,
    _resolve_module_ids,
    render,
    run,
)

__all__ = [
    "REDUCER_META",
    "render",
    "run",
    "_resolve_module",
    "_resolve_module_ids",
    "_list_module_files",
    "_module_file_entries",
    "_list_children",
    "_list_imports",
    "_language_breakdown",
    "_list_methods",
]
