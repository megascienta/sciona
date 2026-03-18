# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript structural-node extraction interfaces."""

from __future__ import annotations

from .javascript_node_state import JavaScriptNodeState
from .javascript_node_walk import walk_javascript_nodes


__all__ = ["JavaScriptNodeState", "walk_javascript_nodes"]
