# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility shim for symbol_references reducer."""

from __future__ import annotations

from ..symbol_references import (
    REDUCER_META,
    _NODE_TYPES,
    _build_references,
    _call_references,
    _fetch_candidates,
    _import_references,
    _node_lookup,
    _normalize_kind,
    _normalize_limit,
    _rank_candidates,
    _score_identifier,
    render,
)

__all__ = [
    "REDUCER_META",
    "_NODE_TYPES",
    "render",
    "_normalize_kind",
    "_normalize_limit",
    "_fetch_candidates",
    "_rank_candidates",
    "_score_identifier",
    "_build_references",
    "_call_references",
    "_import_references",
    "_node_lookup",
]
