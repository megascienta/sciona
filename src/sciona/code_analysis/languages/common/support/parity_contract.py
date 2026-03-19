# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Executable language-parity contract for code-analysis."""

from __future__ import annotations

from ..contracts.loader import load_contract_json

PARITY_CONTRACT_VERSION = 7


def build_parity_contract() -> dict[str, object]:
    """Return a machine-readable parity contract for builtin languages."""
    payload = load_contract_json("parity_contract.json")
    payload["version"] = PARITY_CONTRACT_VERSION
    return payload
