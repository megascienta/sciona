# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for call extraction query helpers."""

from __future__ import annotations

from .call_extraction.queries import normalize_call_identifiers

__all__ = ["normalize_call_identifiers"]
