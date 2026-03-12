# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helper wrappers for canonical callsite diagnostics retrieval."""

from __future__ import annotations

from pathlib import Path

from .graph_edges import load_call_resolution_diagnostics, load_callsite_pairs


def load_callsite_enrichment(
    *,
    repo_root: Path,
    snapshot_id: str,
    caller_id: str,
    identifier: str | None = None,
) -> tuple[list[dict], dict]:
    callsite_pairs = load_callsite_pairs(
        repo_root,
        snapshot_id=snapshot_id,
        caller_id=caller_id,
        identifier=identifier,
    )
    diagnostics = load_call_resolution_diagnostics(
        repo_root,
        snapshot_id=snapshot_id,
        caller_id=caller_id,
    )
    return callsite_pairs, diagnostics


__all__ = ["load_callsite_enrichment"]
