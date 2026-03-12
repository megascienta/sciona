# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helpers for deterministic callsite pair materialization."""

from __future__ import annotations

from ....runtime.common import identity as ids


def build_site_hash(
    *,
    snapshot_id: str,
    caller_id: str,
    identifier: str,
    call_ordinal: int,
) -> str:
    return ids.structural_id(
        "call_site",
        "artifact",
        f"{snapshot_id}:{caller_id}:{identifier}:{call_ordinal}",
    )


def build_pair_hash(
    *,
    snapshot_id: str,
    caller_id: str,
    identifier: str,
    callee_id: str,
    pair_kind: str,
) -> str:
    return ids.structural_id(
        "callsite_pair",
        "artifact",
        (f"{snapshot_id}:{caller_id}:{identifier}:{callee_id}:{pair_kind}"),
    )


__all__ = ["build_pair_hash", "build_site_hash"]
