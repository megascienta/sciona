# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay summary helpers."""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable


def summarize_overlay(
    rows: Iterable[dict[str, object]],
    call_rows: Iterable[dict[str, object]],
) -> dict[str, object] | None:
    node_counts = Counter()
    node_type_counts: dict[str, Counter] = {}
    edge_counts = Counter()
    edge_type_counts: dict[str, Counter] = {}
    for row in rows:
        node_type = row.get("node_type")
        diff_kind = row.get("diff_kind")
        if node_type == "edge":
            edge_counts[diff_kind] += 1
            edge_type = None
            edge_value_raw = row.get("new_value") or row.get("old_value")
            if edge_value_raw:
                try:
                    edge_value = json.loads(edge_value_raw)
                    edge_type = edge_value.get("edge_type")
                except Exception:
                    edge_type = None
            if edge_type:
                edge_type_counts.setdefault(edge_type, Counter())[diff_kind] += 1
            continue
        node_counts[diff_kind] += 1
        if node_type:
            node_type_counts.setdefault(str(node_type), Counter())[diff_kind] += 1

    call_counts = Counter()
    for row in call_rows:
        diff_kind = row.get("diff_kind")
        call_counts[diff_kind] += 1

    def _counter_payload(counter: Counter) -> dict[str, int]:
        return {
            "add": int(counter.get("add", 0)),
            "modify": int(counter.get("modify", 0)),
            "remove": int(counter.get("remove", 0)),
        }

    summary = {
        "nodes": {
            "total": _counter_payload(node_counts),
            "by_type": {
                node_type: _counter_payload(counts)
                for node_type, counts in sorted(node_type_counts.items())
            },
        },
        "edges": {
            "total": {
                "add": int(edge_counts.get("add", 0)),
                "remove": int(edge_counts.get("remove", 0)),
            },
            "by_type": {
                edge_type: {
                    "add": int(counts.get("add", 0)),
                    "remove": int(counts.get("remove", 0)),
                }
                for edge_type, counts in sorted(edge_type_counts.items())
            },
        },
        "calls": {
            "add": int(call_counts.get("add", 0)),
            "remove": int(call_counts.get("remove", 0)),
        },
    }
    if (
        summary["nodes"]["total"] == {"add": 0, "modify": 0, "remove": 0}
        and summary["edges"]["total"] == {"add": 0, "remove": 0}
        and summary["calls"] == {"add": 0, "remove": 0}
    ):
        return None
    return summary


__all__ = ["summarize_overlay"]
