# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript import extraction wrappers."""

from __future__ import annotations

from ...common.query_surface import (
    JAVASCRIPT_DYNAMIC_IMPORT_NODE_TYPES,
    JAVASCRIPT_IMPORT_EXPORT_NODE_TYPES,
    JAVASCRIPT_REQUIRE_DECLARATION_NODE_TYPES,
    TYPESCRIPT_STRING_NODE_TYPES,
)
from ..typescript.typescript_imports import collect_typescript_import_model


def collect_javascript_import_model(root, snapshot, module_name: str, *, module_index):
    return collect_typescript_import_model(
        root,
        snapshot,
        module_name,
        module_index=module_index,
        language_name="javascript",
        import_export_node_types=JAVASCRIPT_IMPORT_EXPORT_NODE_TYPES,
        require_declaration_node_types=JAVASCRIPT_REQUIRE_DECLARATION_NODE_TYPES,
        dynamic_import_node_types=JAVASCRIPT_DYNAMIC_IMPORT_NODE_TYPES,
        string_node_types=TYPESCRIPT_STRING_NODE_TYPES,
    )


__all__ = ["collect_javascript_import_model"]

