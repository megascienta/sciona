# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Declarative walker capability map by language."""

from __future__ import annotations

from ....contracts.declarative.loader import load_contract_json

def build_walker_capabilities() -> dict[str, list[dict[str, object]]]:
    """Return per-language construct coverage mapped to structural emissions."""
    payload = load_contract_json("walker_capabilities.json")
    return {language: list(entries) for language, entries in payload.items()}
