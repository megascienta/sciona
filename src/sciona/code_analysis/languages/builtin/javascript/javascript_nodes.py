# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""JavaScript structural-node extraction wrappers."""

from __future__ import annotations

from ..typescript.typescript_nodes import TypeScriptNodeState, walk_typescript_nodes


def walk_javascript_nodes(*args, **kwargs):
    """Reuse the TypeScript walker with JavaScript query surfaces."""
    kwargs.setdefault("syntax_language", "javascript")
    return walk_typescript_nodes(*args, **kwargs)


__all__ = ["TypeScriptNodeState", "walk_javascript_nodes"]

