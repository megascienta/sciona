# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility wrapper for call extraction type helpers."""

from __future__ import annotations

from .call_extraction.types import (
    CallExtractionRecord,
    CallTarget,
    CallTargetIR,
    QualifiedCallIR,
    ReceiverCallIR,
    TerminalCallIR,
)

__all__ = [
    "CallExtractionRecord",
    "CallTarget",
    "CallTargetIR",
    "QualifiedCallIR",
    "ReceiverCallIR",
    "TerminalCallIR",
]
