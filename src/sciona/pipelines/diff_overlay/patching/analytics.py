# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay patching for reducer payloads."""

from __future__ import annotations

from collections import Counter
import json
from typing import Optional

from ..types import OverlayPayload
from .fan_utils import (
    _fan_deltas_for_node,
    _match_module_name,
    _module_for_node,
    _node_meta_lookup,
    _patch_fan_table,
)
from .shared_delta import (
    apply_call_edge_delta,
    normalize_transition,
    sorted_call_edge_entries,
    summarize_transitions,
    summarize_unique_row_origins,
)
from .shared import edge_from_value, iter_edge_changes, iter_node_changes, node_from_value

def patch_call_neighbors(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("callable_id")
    if not target_id:
        return payload
    callers = {
        entry.get("structural_id"): entry for entry in payload.get("callers", []) or []
    }
    callees = {
        entry.get("structural_id"): entry for entry in payload.get("callees", []) or []
    }
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id or dst_id == target_id:
            if src_id:
                ids_needed.add(str(src_id))
            if dst_id:
                ids_needed.add(str(dst_id))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _entry(node_id: str) -> dict[str, object] | None:
        meta = meta_lookup.get(node_id, {})
        qualified = meta.get("qualified_name")
        node_type = meta.get("node_type")
        if not qualified or not node_type:
            return None
        return {
            "structural_id": node_id,
            "qualified_name": qualified,
            "node_type": node_type,
        }

    for change in overlay.calls.get("add", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id and dst_id:
            entry = _entry(str(dst_id))
            if entry:
                callees[str(dst_id)] = entry
        if dst_id == target_id and src_id:
            entry = _entry(str(src_id))
            if entry:
                callers[str(src_id)] = entry
    for change in overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id and dst_id:
            callees.pop(str(dst_id), None)
        if dst_id == target_id and src_id:
            callers.pop(str(src_id), None)

    payload["callers"] = sorted(
        callers.values(), key=lambda item: str(item.get("qualified_name"))
    )
    payload["callees"] = sorted(
        callees.values(), key=lambda item: str(item.get("qualified_name"))
    )
    payload["caller_count"] = len(payload["callers"])
    payload["callee_count"] = len(payload["callees"])
    return payload

def patch_module_call_graph_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("module_structural_id")
    if not target_id:
        return payload
    top_k = payload.get("top_k")
    outgoing_map: dict[tuple[str, str], dict[str, object]] = {}
    incoming_map: dict[tuple[str, str], dict[str, object]] = {}
    for entry in payload.get("outgoing", []) or []:
        key = (
            str(entry.get("src_module_structural_id") or ""),
            str(entry.get("dst_module_structural_id") or ""),
        )
        outgoing_map[key] = dict(entry)
    for entry in payload.get("incoming", []) or []:
        key = (
            str(entry.get("src_module_structural_id") or ""),
            str(entry.get("dst_module_structural_id") or ""),
        )
        incoming_map[key] = dict(entry)
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        if change.get("src_structural_id"):
            ids_needed.add(str(change.get("src_structural_id")))
        if change.get("dst_structural_id"):
            ids_needed.add(str(change.get("dst_structural_id")))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)
    module_rows = conn.execute(
        """
        SELECT sn.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
          ON ni.structural_id = sn.structural_id
         AND ni.snapshot_id = ?
        WHERE sn.node_type = 'module'
        """,
        (snapshot_id,),
    ).fetchall()
    module_id_by_name = {
        str(row["qualified_name"]): str(row["structural_id"])
        for row in module_rows
        if row["qualified_name"] and row["structural_id"]
    }

    def _module_id(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        module_name = _module_for_node(
            str(meta.get("node_type") or ""), str(meta.get("qualified_name") or "")
        )
        if not module_name:
            return None
        return module_id_by_name.get(module_name)

    changes = overlay.calls.get("add", []) + overlay.calls.get("remove", [])
    for change in changes:
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        src_module = _module_id(str(src_id))
        dst_module = _module_id(str(dst_id))
        if not src_module or not dst_module:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1
        src_name = _module_for_node(
            str(meta_lookup.get(str(src_id), {}).get("node_type") or ""),
            str(meta_lookup.get(str(src_id), {}).get("qualified_name") or ""),
        )
        dst_name = _module_for_node(
            str(meta_lookup.get(str(dst_id), {}).get("node_type") or ""),
            str(meta_lookup.get(str(dst_id), {}).get("qualified_name") or ""),
        )

        def _apply_delta(
            edge_map: dict[tuple[str, str], dict[str, object]],
            *,
            key: tuple[str, str],
            direction: str,
        ) -> None:
            edge_map[key] = apply_call_edge_delta(
                edge_map.get(key),
                delta=delta,
                direction=direction,
                field_updates={
                    "src_module_structural_id": key[0],
                    "dst_module_structural_id": key[1],
                    "src_module_qualified_name": src_name or key[0],
                    "dst_module_qualified_name": dst_name or key[1],
                },
            )

        if src_module == target_id:
            _apply_delta(
                outgoing_map,
                key=(src_module, dst_module),
                direction="outgoing",
            )
        if dst_module == target_id:
            _apply_delta(
                incoming_map,
                key=(src_module, dst_module),
                direction="incoming",
            )

    outgoing_all = sorted_call_edge_entries(
        outgoing_map,
        top_k=top_k,
        src_field="src_module_qualified_name",
        dst_field="dst_module_qualified_name",
    )
    incoming_all = sorted_call_edge_entries(
        incoming_map,
        top_k=top_k,
        src_field="src_module_qualified_name",
        dst_field="dst_module_qualified_name",
    )
    payload["outgoing"] = outgoing_all
    payload["incoming"] = incoming_all
    payload["outgoing_count"] = sum(1 for item in outgoing_all if item.get("is_active"))
    payload["incoming_count"] = sum(1 for item in incoming_all if item.get("is_active"))
    payload["outgoing_total"] = payload["outgoing_count"]
    payload["incoming_total"] = payload["incoming_count"]
    payload["outgoing_listed_count"] = len(outgoing_all)
    payload["incoming_listed_count"] = len(incoming_all)
    payload["total_edges"] = len(outgoing_all) + len(incoming_all)
    payload.update(
        summarize_unique_row_origins(
            outgoing_all + incoming_all,
            key_fields=("src_module_structural_id", "dst_module_structural_id"),
        )
    )
    payload["edge_summary"] = {
        "CALLS": {
            "outgoing": payload["outgoing_total"],
            "incoming": payload["incoming_total"],
        }
    }
    if outgoing_all:
        payload["outgoing_coverage_ratio"] = 1.0
    if incoming_all:
        payload["incoming_coverage_ratio"] = 1.0
    return payload

def patch_classifier_call_graph_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("classifier_structural_id")
    if not target_id:
        return payload
    top_k = payload.get("top_k")
    outgoing_map: dict[tuple[str, str], dict[str, object]] = {}
    incoming_map: dict[tuple[str, str], dict[str, object]] = {}
    for entry in payload.get("outgoing", []) or []:
        key = (
            str(entry.get("src_classifier_id")),
            str(entry.get("dst_classifier_id")),
        )
        outgoing_map[key] = dict(entry)
    for entry in payload.get("incoming", []) or []:
        key = (
            str(entry.get("src_classifier_id")),
            str(entry.get("dst_classifier_id")),
        )
        incoming_map[key] = dict(entry)
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        if change.get("src_structural_id"):
            ids_needed.add(str(change.get("src_structural_id")))
        if change.get("dst_structural_id"):
            ids_needed.add(str(change.get("dst_structural_id")))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)
    classifier_rows = conn.execute(
        """
        SELECT sn.structural_id, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni
          ON ni.structural_id = sn.structural_id
         AND ni.snapshot_id = ?
        WHERE sn.node_type = 'classifier'
        """,
        (snapshot_id,),
    ).fetchall()
    classifier_id_by_name = {
        str(row["qualified_name"]): str(row["structural_id"])
        for row in classifier_rows
        if row["qualified_name"] and row["structural_id"]
    }

    def _classifier_id(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        if meta.get("node_type") != "callable":
            return None
        qualified = str(meta.get("qualified_name") or "")
        parts = qualified.split(".")
        if len(parts) < 2:
            return None
        classifier_name = ".".join(parts[:-1])
        return classifier_id_by_name.get(classifier_name)

    changes = overlay.calls.get("add", []) + overlay.calls.get("remove", [])
    for change in changes:
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        src_classifier = _classifier_id(str(src_id))
        dst_classifier = _classifier_id(str(dst_id))
        if not src_classifier or not dst_classifier:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1
        src_name = str(meta_lookup.get(str(src_id), {}).get("qualified_name") or "")
        dst_name = str(meta_lookup.get(str(dst_id), {}).get("qualified_name") or "")
        src_classifier_name = ".".join(src_name.split(".")[:-1]) if src_name else None
        dst_classifier_name = ".".join(dst_name.split(".")[:-1]) if dst_name else None

        def _apply_delta(
            edge_map: dict[tuple[str, str], dict[str, object]],
            *,
            key: tuple[str, str],
            direction: str,
        ) -> None:
            edge_map[key] = apply_call_edge_delta(
                edge_map.get(key),
                delta=delta,
                direction=direction,
                field_updates={
                    "src_classifier_id": key[0],
                    "dst_classifier_id": key[1],
                    "src_classifier_qualified_name": src_classifier_name,
                    "dst_classifier_qualified_name": dst_classifier_name,
                },
            )

        if src_classifier == target_id:
            _apply_delta(
                outgoing_map,
                key=(src_classifier, dst_classifier),
                direction="outgoing",
            )
        if dst_classifier == target_id:
            _apply_delta(
                incoming_map,
                key=(src_classifier, dst_classifier),
                direction="incoming",
            )

    outgoing_all = sorted_call_edge_entries(
        outgoing_map,
        top_k=top_k,
        src_field="src_classifier_id",
        dst_field="dst_classifier_id",
    )
    incoming_all = sorted_call_edge_entries(
        incoming_map,
        top_k=top_k,
        src_field="src_classifier_id",
        dst_field="dst_classifier_id",
    )
    payload["outgoing"] = outgoing_all
    payload["incoming"] = incoming_all
    payload["outgoing_count"] = sum(1 for item in outgoing_all if item.get("is_active"))
    payload["incoming_count"] = sum(1 for item in incoming_all if item.get("is_active"))
    payload["outgoing_total"] = payload["outgoing_count"]
    payload["incoming_total"] = payload["incoming_count"]
    payload["outgoing_listed_count"] = len(outgoing_all)
    payload["incoming_listed_count"] = len(incoming_all)
    payload["total_edges"] = len(outgoing_all) + len(incoming_all)
    payload.update(
        summarize_unique_row_origins(
            outgoing_all + incoming_all,
            key_fields=("src_classifier_id", "dst_classifier_id"),
        )
    )
    payload["edge_summary"] = {
        "CALLS": {
            "outgoing": payload["outgoing_total"],
            "incoming": payload["incoming_total"],
        }
    }
    if outgoing_all:
        payload["outgoing_coverage_ratio"] = 1.0
    if incoming_all:
        payload["incoming_coverage_ratio"] = 1.0
    return payload


def patch_call_resolution_quality(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    transition_counts = _overlay_transition_counts(overlay)
    delta_totals = {
        "eligible": 0,
        "accepted": transition_counts["dropped_to_accepted"]
        - transition_counts["accepted_to_dropped"],
        "dropped": transition_counts["accepted_to_dropped"]
        - transition_counts["dropped_to_accepted"],
    }
    committed = dict(payload.get("committed_totals") or payload.get("totals") or {})
    adjusted = {
        "eligible": int(committed.get("eligible") or 0),
        "accepted": max(
            0, int(committed.get("accepted") or 0) + int(delta_totals["accepted"])
        ),
        "dropped": max(
            0, int(committed.get("dropped") or 0) + int(delta_totals["dropped"])
        ),
    }
    adjusted["acceptance_rate"] = (
        float(adjusted["accepted"]) / float(adjusted["eligible"])
        if adjusted["eligible"] > 0
        else None
    )
    payload["committed_totals"] = {
        "eligible": int(committed.get("eligible") or 0),
        "accepted": int(committed.get("accepted") or 0),
        "dropped": int(committed.get("dropped") or 0),
        "acceptance_rate": committed.get("acceptance_rate"),
    }
    payload["overlay_adjusted_totals"] = adjusted
    payload["overlay_delta_totals"] = delta_totals
    payload["overlay_transition_counts"] = transition_counts
    payload["totals"] = adjusted
    payload["by_caller"] = _patch_quality_by_caller(
        list(payload.get("by_caller") or []),
        overlay,
        snapshot_id=snapshot_id,
        conn=conn,
    )
    return payload


def patch_call_resolution_drop_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    transition_counts = _overlay_transition_counts(overlay)
    delta_totals = {
        "eligible": 0,
        "accepted": transition_counts["dropped_to_accepted"]
        - transition_counts["accepted_to_dropped"],
        "dropped": transition_counts["accepted_to_dropped"]
        - transition_counts["dropped_to_accepted"],
    }
    committed = dict(payload.get("committed_totals") or payload.get("totals") or {})
    adjusted = {
        "eligible": int(committed.get("eligible") or 0),
        "accepted": max(
            0, int(committed.get("accepted") or 0) + int(delta_totals["accepted"])
        ),
        "dropped": max(
            0, int(committed.get("dropped") or 0) + int(delta_totals["dropped"])
        ),
    }
    adjusted["drop_rate"] = (
        round(adjusted["dropped"] / adjusted["eligible"], 6)
        if adjusted["eligible"] > 0
        else None
    )
    payload["committed_totals"] = {
        "eligible": int(committed.get("eligible") or 0),
        "accepted": int(committed.get("accepted") or 0),
        "dropped": int(committed.get("dropped") or 0),
        "drop_rate": committed.get("drop_rate"),
    }
    payload["overlay_adjusted_totals"] = adjusted
    payload["overlay_delta_totals"] = delta_totals
    payload["overlay_transition_counts"] = transition_counts
    payload["overlay_drop_reason_delta"] = _overlay_drop_reason_delta_entries(
        transition_counts
    )
    payload["totals"] = adjusted
    payload["top_changed_callers"] = _overlay_changed_callers(
        overlay,
        snapshot_id=snapshot_id,
        conn=conn,
        limit=int(payload.get("limit") or 10),
    )
    return payload


def _overlay_transition_counts(overlay: OverlayPayload) -> dict[str, int]:
    return {
        "accepted_to_dropped": len(overlay.calls.get("remove", [])),
        "dropped_to_accepted": len(overlay.calls.get("add", [])),
    }


def _patch_quality_by_caller(
    rows: list[dict[str, object]],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> list[dict[str, object]]:
    caller_deltas = _caller_transition_deltas(overlay)
    ids_needed = set(caller_deltas)
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)
    by_caller = {
        str(row.get("caller_id") or ""): dict(row) for row in rows if row.get("caller_id")
    }
    for caller_id, delta in caller_deltas.items():
        row = dict(by_caller.get(caller_id) or {})
        committed_accepted = int(row.get("accepted") or 0)
        committed_dropped = int(row.get("dropped") or 0)
        eligible = int(row.get("eligible") or (committed_accepted + committed_dropped))
        meta = meta_lookup.get(caller_id, {})
        row.update(
            {
                "caller_id": caller_id,
                "qualified_name": row.get("qualified_name") or meta.get("qualified_name"),
                "language": row.get("language") or meta.get("language"),
                "module_qualified_name": row.get("module_qualified_name")
                or _module_for_node(
                    str(meta.get("node_type") or ""),
                    str(meta.get("qualified_name") or ""),
                ),
                "file_path": row.get("file_path") or meta.get("file_path"),
                "eligible": eligible,
                "accepted": max(0, committed_accepted + delta["accepted"]),
                "dropped": max(0, committed_dropped + delta["dropped"]),
                "accepted_delta": delta["accepted"],
                "dropped_delta": delta["dropped"],
            }
        )
        row["acceptance_rate"] = (
            float(row["accepted"]) / float(eligible) if eligible > 0 else None
        )
        by_caller[caller_id] = row
    result = list(by_caller.values())
    result.sort(
        key=lambda item: (
            -abs(int(item.get("accepted_delta") or 0) - int(item.get("dropped_delta") or 0)),
            -int(item.get("eligible") or 0),
            str(item.get("qualified_name") or ""),
        )
    )
    return result


def _overlay_drop_reason_delta_entries(
    transition_counts: dict[str, int],
) -> list[dict[str, object]]:
    entries = []
    for name, count in {
        "overlay_unclassified_drop": int(transition_counts["accepted_to_dropped"]),
        "overlay_unclassified_resolution": -int(
            transition_counts["dropped_to_accepted"]
        ),
    }.items():
        if count:
            entries.append({"name": name, "delta_count": count})
    entries.sort(key=lambda item: (-abs(int(item["delta_count"])), str(item["name"])))
    return entries


def _overlay_changed_callers(
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
    limit: int,
) -> list[dict[str, object]]:
    caller_deltas = _caller_transition_deltas(overlay)
    ids_needed = set(caller_deltas)
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)
    rows = []
    for caller_id, delta in caller_deltas.items():
        meta = meta_lookup.get(caller_id, {})
        rows.append(
            {
                "caller_id": caller_id,
                "qualified_name": meta.get("qualified_name"),
                "language": meta.get("language"),
                "module_qualified_name": _module_for_node(
                    str(meta.get("node_type") or ""),
                    str(meta.get("qualified_name") or ""),
                ),
                "file_path": meta.get("file_path"),
                "accepted_delta": delta["accepted"],
                "dropped_delta": delta["dropped"],
            }
        )
    rows.sort(
        key=lambda item: (
            -abs(int(item.get("accepted_delta") or 0) - int(item.get("dropped_delta") or 0)),
            str(item.get("qualified_name") or ""),
            str(item.get("caller_id") or ""),
        )
    )
    return rows[:limit]


def _caller_transition_deltas(overlay: OverlayPayload) -> dict[str, dict[str, int]]:
    deltas: dict[str, dict[str, int]] = {}
    for change in overlay.calls.get("add", []):
        caller_id = str(change.get("src_structural_id") or "")
        if not caller_id:
            continue
        entry = deltas.setdefault(caller_id, {"accepted": 0, "dropped": 0})
        entry["accepted"] += 1
        entry["dropped"] -= 1
    for change in overlay.calls.get("remove", []):
        caller_id = str(change.get("src_structural_id") or "")
        if not caller_id:
            continue
        entry = deltas.setdefault(caller_id, {"accepted": 0, "dropped": 0})
        entry["accepted"] -= 1
        entry["dropped"] += 1
    return deltas

def patch_fan_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    node_id = payload.get("node_id")
    if node_id:
        edge_kinds = dict(payload.get("edge_kinds") or {})
        deltas = _fan_deltas_for_node(overlay, str(node_id))
        for edge_kind, delta_map in deltas.items():
            entry = dict(edge_kinds.get(edge_kind) or {})
            committed_in = int(entry.get("committed_fan_in") or entry.get("fan_in") or 0)
            committed_out = int(entry.get("committed_fan_out") or entry.get("fan_out") or 0)
            entry["fan_in"] = max(0, committed_in + delta_map.get("fan_in", 0))
            entry["fan_out"] = max(0, committed_out + delta_map.get("fan_out", 0))
            entry["committed_fan_in"] = committed_in
            entry["committed_fan_out"] = committed_out
            entry["delta_fan_in"] = int(entry["fan_in"]) - committed_in
            entry["delta_fan_out"] = int(entry["fan_out"]) - committed_out
            edge_kinds[edge_kind] = entry
        payload["edge_kinds"] = edge_kinds
        payload["edge_summary"] = edge_kinds
        return payload

    calls_table = dict(payload.get("calls") or {})
    imports_table = dict(payload.get("imports") or {})
    payload["calls"] = _patch_fan_table(
        calls_table,
        overlay,
        edge_kind="CALLS",
        snapshot_id=snapshot_id,
        conn=conn,
    )
    payload["imports"] = _patch_fan_table(
        imports_table,
        overlay,
        edge_kind="IMPORTS_DECLARED",
        snapshot_id=snapshot_id,
        conn=conn,
    )
    return payload

def patch_hotspot_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    by_size = list(payload.get("by_size", []) or [])
    size_map = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in by_size}
    module_names = [name for name in size_map.keys() if name]
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type") or "")
        if node_type not in {"classifier", "callable"}:
            continue
        module_name = _match_module_name(
            str(node.get("qualified_name") or ""), module_names
        )
        if module_name not in size_map:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1 if change.get("diff_kind") == "remove" else 0
        if delta:
            size_map[module_name] = max(0, size_map.get(module_name, 0) + delta)

    by_size = [
        {"module_qualified_name": name, "count": count}
        for name, count in size_map.items()
    ]
    by_size.sort(key=lambda item: (-int(item.get("count") or 0), str(item.get("module_qualified_name"))))
    payload["by_size"] = by_size[: len(payload.get("by_size", []) or [])]

    fan_in = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in payload.get("by_fan_in", []) or []}
    fan_out = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in payload.get("by_fan_out", []) or []}
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_name = edge.get("src_qualified_name")
        dst_name = edge.get("dst_qualified_name")
        delta = 1 if change.get("diff_kind") == "add" else -1 if change.get("diff_kind") == "remove" else 0
        if delta:
            if src_name in fan_out:
                fan_out[src_name] = max(0, fan_out.get(src_name, 0) + delta)
            if dst_name in fan_in:
                fan_in[dst_name] = max(0, fan_in.get(dst_name, 0) + delta)
    payload["by_fan_in"] = [
        {"module_qualified_name": name, "count": count}
        for name, count in sorted(fan_in.items(), key=lambda item: (-item[1], str(item[0])))
    ][: len(payload.get("by_fan_in", []) or [])]
    payload["by_fan_out"] = [
        {"module_qualified_name": name, "count": count}
        for name, count in sorted(fan_out.items(), key=lambda item: (-item[1], str(item[0])))
    ][: len(payload.get("by_fan_out", []) or [])]
    return payload
