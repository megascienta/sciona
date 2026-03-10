# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Shared delta helpers for overlay patchers."""

from __future__ import annotations

from typing import Iterable


def normalize_row_origin(entry: dict[str, object]) -> dict[str, object]:
    item = dict(entry)
    item["row_origin"] = str(item.get("row_origin") or "committed")
    return item


def normalize_transition(entry: dict[str, object]) -> dict[str, object]:
    item = normalize_row_origin(entry)
    item["transition"] = str(item.get("transition") or "unchanged")
    return item


def apply_call_edge_delta(
    entry: dict[str, object] | None,
    *,
    delta: int,
    direction: str,
    field_updates: dict[str, object],
) -> dict[str, object]:
    row = dict(entry or {})
    committed = int(row.get("committed_call_count") or row.get("call_count") or 0)
    overlay_count = int(row.get("overlay_call_count") or committed)
    overlay_count = max(0, overlay_count + delta)
    row.update(field_updates)
    row.update(
        {
            "direction": direction,
            "committed_call_count": committed,
            "overlay_call_count": overlay_count,
            "delta_call_count": overlay_count - committed,
            "call_count": overlay_count,
            "is_active": overlay_count > 0,
        }
    )
    if committed == 0 and overlay_count > 0:
        row["row_origin"] = "overlay_added"
    elif committed > 0 and overlay_count == 0:
        row["row_origin"] = "overlay_removed"
    elif committed != overlay_count:
        row["row_origin"] = "overlay_changed"
    else:
        row["row_origin"] = "committed"
    return row


def sorted_call_edge_entries(
    edge_map: dict[tuple[str, str], dict[str, object]],
    *,
    top_k: object,
    src_field: str,
    dst_field: str,
) -> list[dict[str, object]]:
    entries = [dict(row) for row in edge_map.values()]
    entries.sort(
        key=lambda item: (
            -int(item.get("overlay_call_count") or item.get("call_count") or 0),
            str(item.get(src_field)),
            str(item.get(dst_field)),
        )
    )
    if top_k is not None:
        try:
            limit = int(top_k)
        except (TypeError, ValueError):
            limit = None
        if limit and limit > 0:
            entries = entries[:limit]
    return entries


def summarize_unique_row_origins(
    rows: Iterable[dict[str, object]],
    *,
    key_fields: tuple[str, str],
) -> dict[str, int]:
    unique_rows = {
        (str(row.get(key_fields[0]) or ""), str(row.get(key_fields[1]) or "")): row
        for row in rows
    }.values()
    return {
        "added_edge_count": sum(
            1 for row in unique_rows if row.get("row_origin") == "overlay_added"
        ),
        "removed_edge_count": sum(
            1 for row in unique_rows if row.get("row_origin") == "overlay_removed"
        ),
        "changed_edge_count": sum(
            1
            for row in unique_rows
            if row.get("row_origin") in {"overlay_added", "overlay_removed", "overlay_changed"}
        ),
    }


def summarize_transitions(rows: Iterable[dict[str, object]]) -> dict[str, int]:
    rows = list(rows)
    return {
        "unchanged": sum(1 for row in rows if row.get("transition") == "unchanged"),
        "accepted_to_dropped": sum(
            1 for row in rows if row.get("transition") == "accepted_to_dropped"
        ),
        "dropped_to_accepted": sum(
            1 for row in rows if row.get("transition") == "dropped_to_accepted"
        ),
        "provenance_changed": sum(
            1 for row in rows if row.get("transition") == "provenance_changed"
        ),
    }
