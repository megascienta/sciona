# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility exports for shared reducer query helpers."""

from __future__ import annotations

from .id_resolution import resolve_callable_id, resolve_classifier_id
from .module_context import (
    collect_file_paths,
    list_modules,
    module_id_for_structural,
    module_id_lookup,
    module_root_paths,
    resolve_module_root,
)
from .relationships import fetch_children, fetch_class_relationships

__all__ = [
    "collect_file_paths",
    "fetch_children",
    "fetch_class_relationships",
    "list_modules",
    "module_id_for_structural",
    "module_id_lookup",
    "module_root_paths",
    "resolve_callable_id",
    "resolve_classifier_id",
    "resolve_module_root",
]
