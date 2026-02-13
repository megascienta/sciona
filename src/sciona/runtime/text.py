# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared text normalization helpers."""

from __future__ import annotations


def canonical_span_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if normalized.endswith("\n") and len(normalized) > 1:
        normalized = normalized[:-1]
    return normalized


def canonical_span_bytes(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    if normalized.endswith(b"\n") and len(normalized) > 1:
        normalized = normalized[:-1]
    return normalized
