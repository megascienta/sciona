# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Time helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
