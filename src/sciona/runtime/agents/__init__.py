# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""AGENTS.md and CLAUDE.md generation helpers."""

from .setup import build_agents_block, remove_agents_block, upsert_agents_file
from .claude_setup import build_claude_block, remove_claude_block, upsert_claude_file
from .settings_setup import upsert_claude_settings, remove_claude_settings

__all__ = [
    "build_agents_block",
    "remove_agents_block",
    "upsert_agents_file",
    "build_claude_block",
    "remove_claude_block",
    "upsert_claude_file",
    "upsert_claude_settings",
    "remove_claude_settings",
]
