# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helper wrappers for artifact call_sites retrieval."""

from __future__ import annotations

from pathlib import Path

from .artifact_graph_edges import load_call_resolution_diagnostics, load_call_sites


def load_callsite_enrichment(
    *,
    repo_root: Path,
    snapshot_id: str,
    caller_id: str,
) -> tuple[list[dict], dict]:
    call_sites = load_call_sites(
        repo_root,
        snapshot_id=snapshot_id,
        caller_id=caller_id,
    )
    diagnostics = load_call_resolution_diagnostics(
        repo_root,
        snapshot_id=snapshot_id,
        caller_id=caller_id,
    )
    return call_sites, diagnostics


__all__ = ["load_callsite_enrichment"]
