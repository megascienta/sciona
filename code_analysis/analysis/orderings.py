"""Shared ordering helpers for projection payloads."""

from __future__ import annotations

from typing import Any, Callable, Dict, Sequence


def order_nodes(
    entries: Any,
    key: str | Callable[[Dict[str, Any]], Any] = "qualified_name",
) -> Any:
    """Sort a list of node dictionaries in place."""
    if not isinstance(entries, list):
        return entries
    if callable(key):
        entries.sort(key=key)
    else:
        entries.sort(key=lambda item: item.get(key, ""))
    return entries


def order_edges(
    entries: Any,
    fields: Sequence[str] | None = None,
    key: Callable[[Dict[str, Any]], Any] | None = None,
) -> Any:
    """Sort edge dictionaries deterministically."""
    if not isinstance(entries, list):
        return entries
    if key is not None:
        entries.sort(key=key)
        return entries
    fields = fields or ("src_structural_id", "dst_structural_id", "edge_type")
    entries.sort(key=lambda item: tuple(item.get(field, "") for field in fields))
    return entries


def order_strings(entries: Any) -> Any:
    """Sort a list of scalar strings in place."""
    if isinstance(entries, list):
        entries.sort()
    return entries
