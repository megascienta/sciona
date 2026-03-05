# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""TypeScript node extraction utilities."""

from __future__ import annotations

from .typescript_node_state import TypeScriptNodeState
from .typescript_node_text import (
    function_body_node,
    name_chain,
    node_text,
    parse_type_annotation,
    typed_constructor_parameters,
)
from .typescript_node_walk import walk_typescript_children, walk_typescript_nodes


__all__ = [
    "TypeScriptNodeState",
    "function_body_node",
    "name_chain",
    "node_text",
    "parse_type_annotation",
    "typed_constructor_parameters",
    "walk_typescript_children",
    "walk_typescript_nodes",
]
