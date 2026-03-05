# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helpers for deterministic call_sites row materialization."""

from __future__ import annotations

from ...runtime import identity as ids


def build_site_hash(
    *,
    snapshot_id: str,
    caller_id: str,
    identifier: str,
    resolution_status: str,
    accepted_callee_id: str | None,
    provenance: str | None,
    drop_reason: str | None,
    candidate_count: int,
    callee_kind: str,
    call_start_byte: int | None,
    call_end_byte: int | None,
    call_ordinal: int,
    in_scope_candidate_count: int | None,
    candidate_module_hints: str | None,
) -> str:
    return ids.structural_id(
        "call_site",
        "artifact",
        (
            f"{snapshot_id}:{caller_id}:{identifier}:{resolution_status}:"
            f"{accepted_callee_id or ''}:{provenance or ''}:{drop_reason or ''}:"
            f"{candidate_count}:{callee_kind}:{call_start_byte}:{call_end_byte}:{call_ordinal}:"
            f"{in_scope_candidate_count}:{candidate_module_hints or ''}"
        ),
    )


__all__ = ["build_site_hash"]
