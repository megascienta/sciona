# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared marker-block utilities for managed file sections."""

from __future__ import annotations

BEGIN_MARKER = "<!-- sciona:begin -->"
END_MARKER = "<!-- sciona:end -->"


def check_not_symlink(path: "Path") -> None:
    """Raise ValueError if path is a symlink to prevent writing through it."""
    if path.is_symlink():
        raise ValueError(
            f"{path.name} is a symbolic link. "
            "Refusing to write through it to avoid corrupting the link target. "
            "Remove or replace the symlink before running this command."
        )


def replace_or_append_block(text: str, block: str) -> str:
    if BEGIN_MARKER in text and END_MARKER in text:
        return replace_block(text, block)
    suffix = "" if text.endswith("\n") else "\n"
    return f"{text}{suffix}\n{block}"


def replace_block(text: str, block: str) -> str:
    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER) + len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    parts = []
    if before:
        parts.append(before)
    parts.append(block.rstrip())
    if after:
        parts.append(after)
    return "\n\n".join(parts).rstrip() + "\n"


def remove_block(text: str) -> str:
    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER) + len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    if before and after:
        return f"{before}\n\n{after}".rstrip() + "\n"
    if before:
        return before.rstrip() + "\n"
    if after:
        return after.rstrip() + "\n"
    return ""


__all__ = [
    "BEGIN_MARKER",
    "END_MARKER",
    "check_not_symlink",
    "replace_or_append_block",
    "replace_block",
    "remove_block",
]
