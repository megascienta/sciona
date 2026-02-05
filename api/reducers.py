"""Reducer API (stable)."""
from __future__ import annotations

from ..pipelines import reducers as reducers_pipeline
from ..reducers.registry import freeze_registry, get_reducers, load_reducer

emit = reducers_pipeline.emit
list_entries = reducers_pipeline.list_entries
get_entry = reducers_pipeline.get_entry

__all__ = [
    "emit",
    "list_entries",
    "get_entry",
    "freeze_registry",
    "get_reducers",
    "load_reducer",
]
