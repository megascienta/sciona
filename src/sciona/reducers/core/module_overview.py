# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Module overview reducer."""

from __future__ import annotations

from ._internal.module_overview_main import REDUCER_META, render, run
from ._internal.module_overview_resolve import (
    _resolve_module,
    _resolve_module_ids,
    _list_module_files,
    _module_file_entries,
)
from ._internal.module_overview_relations import (
    _list_children,
    _list_imports,
    _language_breakdown,
    _list_methods,
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
