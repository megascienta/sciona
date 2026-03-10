# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for analysis strict-call selection contracts."""

from __future__ import annotations

from ..analysis_contracts.strict_call_contract import StrictCallDecision, select_strict_call_candidate

__all__ = ["StrictCallDecision", "select_strict_call_candidate"]
