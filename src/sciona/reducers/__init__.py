# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer root package."""

from __future__ import annotations

from types import SimpleNamespace

from . import callable_overview
from . import classifier_overview
from . import helpers
from . import module_overview
from . import structural_index

# Backward-compatible namespace for structural reducer imports.
core = SimpleNamespace(
    structural_index=structural_index,
    module_overview=module_overview,
    classifier_overview=classifier_overview,
    callable_overview=callable_overview,
)

__all__ = ["helpers", "core"]
