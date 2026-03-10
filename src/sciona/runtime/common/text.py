# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared text normalization helpers."""

from __future__ import annotations


def canonical_span_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    return normalized.rstrip("\n")


def canonical_span_bytes(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    return normalized.rstrip(b"\n")
