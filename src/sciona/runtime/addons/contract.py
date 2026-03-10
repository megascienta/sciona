# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Plugin API version contract for addons."""

from __future__ import annotations

import re
from typing import Tuple

PLUGIN_API_MAJOR = 1
PLUGIN_API_MINOR = 0
PLUGIN_API_VERSION = f"{PLUGIN_API_MAJOR}.{PLUGIN_API_MINOR}"

_RANGE_PATTERN = re.compile(r"^>=\s*(\d+)\s*,\s*<\s*(\d+)\s*$")
_NUMERIC_PATTERN = re.compile(r"^(\d+)(?:\.\d+)?$")


def requirement_compatible(requirement: object) -> Tuple[bool, str | None]:
    """
    Validate addon plugin API requirement against the current core API version.

    Supported requirement forms:
    - None (no requirement)
    - integer major (e.g., 1)
    - string major or major.minor (e.g., "1", "1.0")
    - range string ">=X,<Y" (e.g., ">=1,<2")
    """
    if requirement is None:
        return True, None
    if isinstance(requirement, int):
        return requirement == PLUGIN_API_MAJOR, str(requirement)
    if not isinstance(requirement, str):
        return False, str(requirement)
    text = requirement.strip()
    if not text:
        return True, None
    if text.isdigit():
        return int(text) == PLUGIN_API_MAJOR, text
    range_match = _RANGE_PATTERN.match(text)
    if range_match:
        lower = int(range_match.group(1))
        upper = int(range_match.group(2))
        return lower <= PLUGIN_API_MAJOR < upper, text
    numeric_match = _NUMERIC_PATTERN.match(text)
    if numeric_match:
        return int(numeric_match.group(1)) == PLUGIN_API_MAJOR, text
    return False, text


__all__ = [
    "PLUGIN_API_MAJOR",
    "PLUGIN_API_MINOR",
    "PLUGIN_API_VERSION",
    "requirement_compatible",
]
