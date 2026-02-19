# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol reference reducer."""

from __future__ import annotations

from ._internal.symbol_references_main import REDUCER_META, render
from ._internal.symbol_references_normalize import _NODE_TYPES, _normalize_kind, _normalize_limit
from ._internal.symbol_references_candidates import (
    _fetch_candidates,
    _rank_candidates,
    _score_identifier,
)
from ._internal.symbol_references_references import (
    _build_references,
    _call_references,
    _import_references,
    _node_lookup,
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
