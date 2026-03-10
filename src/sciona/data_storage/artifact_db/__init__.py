# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB namespace (derived, last-committed-snapshot only)."""

from __future__ import annotations

from . import (
    maintenance,
    overlay,
    reporting,
    rollups,
    schema,
    writes,
)
from .connect import connect

__all__ = [
    "connect",
    "maintenance",
    "overlay",
    "reporting",
    "rollups",
    "schema",
    "writes",
]
