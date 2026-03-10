# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI facade for identifier resolution helpers."""

from __future__ import annotations

from ..api import resolve_ops as _resolve_ops

identifier_for_repo = _resolve_ops.identifier_for_repo
identifier = _resolve_ops.identifier
require_identifier = _resolve_ops.require_identifier
format_resolution_message = _resolve_ops.format_resolution_message

__all__ = _resolve_ops.__all__
