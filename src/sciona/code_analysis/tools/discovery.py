# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for workspace discovery helpers."""

from __future__ import annotations

from .workspace.discovery import compute_discovery_details, detect_languages_from_tracked_paths

__all__ = ["compute_discovery_details", "detect_languages_from_tracked_paths"]
