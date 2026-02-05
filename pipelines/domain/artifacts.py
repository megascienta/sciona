"""Artifact-domain derivation logic used by build orchestration."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Sequence

from ...code_analysis.analysis.graph import module_id_for
from ...code_analysis.config import CALLABLE_NODE_TYPES
from ...code_analysis.tools.call_extraction import CallExtractionRecord
from ...data_storage.artifact_db import store as artifact_store
from ...data_storage.artifact_db import store_rollups as artifact_rollups
from ...data_storage.core_db import store as core_store
from ...data_storage.sql_utils import SQLITE_MAX_VARS, chunked


def rebuild_graph_rollups(
    artifact_conn,
    *,
    core_conn,
    snapshot_id: str,
) -> None:
    core_store.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    artifact_rollups.reset_graph_rollups(artifact_conn)
    node_rows = core_conn.execute(
        """
        SELECT sn.structural_id, sn.node_type, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    if not node_rows:
        return
    module_names = {
        row["qualified_name"]
        for row in node_rows
        if row["node_type"] == "module" and row["qualified_name"]
    }
    module_id_by_name = {
        row["qualified_name"]: row["structural_id"]
        for row in node_rows
        if row["node_type"] == "module" and row["qualified_name"]
    }
    module_lookup: dict[str, str] = {}
    node_kind_lookup: dict[str, str] = {}
    for row in node_rows:
        structural_id = row["structural_id"]
        qualified_name = row["qualified_name"]
        node_kind_lookup[structural_id] = row["node_type"]
        if qualified_name:
            module_name = module_id_for(qualified_name, module_names)
            module_structural_id = module_id_by_name.get(module_name)
            if module_structural_id:
                module_lookup[structural_id] = module_structural_id
    method_edges = core_conn.execute(
        """
        SELECT src_structural_id, dst_structural_id
        FROM edges
        WHERE snapshot_id = ?
          AND edge_type = 'DEFINES_METHOD'
        """,
        (snapshot_id,),
    ).fetchall()
    method_to_class = {row["dst_structural_id"]: row["src_structural_id"] for row in method_edges}

    call_rows = artifact_conn.execute(
        """
        SELECT src_node_id, dst_node_id
        FROM graph_edges
        WHERE edge_kind = ?
        """,
        ("CALLS",),
    ).fetchall()
    module_calls: Counter[tuple[str, str]] = Counter()
    class_calls: Counter[tuple[str, str]] = Counter()
    for row in call_rows:
        src_id = row["src_node_id"]
        dst_id = row["dst_node_id"]
        src_module = module_lookup.get(src_id)
        dst_module = module_lookup.get(dst_id)
        if src_module and dst_module:
            module_calls[(src_module, dst_module)] += 1
        src_class = method_to_class.get(src_id)
        dst_class = method_to_class.get(dst_id)
        if src_class and dst_class:
            class_calls[(src_class, dst_class)] += 1
    if module_calls:
        artifact_rollups.insert_module_call_edges(
            artifact_conn,
            rows=[(src, dst, count) for (src, dst), count in module_calls.items()],
        )
    if class_calls:
        artifact_rollups.insert_class_call_edges(
            artifact_conn,
            rows=[(src, dst, count) for (src, dst), count in class_calls.items()],
        )

    fan_in: dict[tuple[str, str], int] = defaultdict(int)
    fan_out: dict[tuple[str, str], int] = defaultdict(int)
    edge_rows = artifact_conn.execute(
        """
        SELECT src_node_id, dst_node_id, edge_kind
        FROM graph_edges
        """,
    ).fetchall()
    for row in edge_rows:
        src_id = row["src_node_id"]
        dst_id = row["dst_node_id"]
        edge_kind = row["edge_kind"]
        fan_out[(src_id, edge_kind)] += 1
        fan_in[(dst_id, edge_kind)] += 1
    if fan_in or fan_out:
        all_keys = set(fan_in) | set(fan_out)
        stats_rows = []
        for node_id, edge_kind in sorted(all_keys):
            stats_rows.append(
                (
                    node_id,
                    node_kind_lookup.get(node_id, ""),
                    edge_kind,
                    fan_in.get((node_id, edge_kind), 0),
                    fan_out.get((node_id, edge_kind), 0),
                )
            )
        artifact_rollups.insert_node_fan_stats(artifact_conn, rows=stats_rows)


def write_call_artifacts(
    *,
    artifact_conn,
    core_conn,
    snapshot_id: str,
    call_records: Sequence[CallExtractionRecord],
    eligible_callers: Iterable[str] | None = None,
) -> None:
    """Write call artifacts for eligible callers."""
    core_store.validate_snapshot_for_read(core_conn, snapshot_id, require_committed=True)
    if not call_records:
        return
    caller_set = (
        set(eligible_callers)
        if eligible_callers is not None
        else {record.caller_structural_id for record in call_records}
    )
    if not caller_set:
        return
    symbol_index = _build_symbol_index(core_conn, snapshot_id)
    node_hashes = _load_node_hashes(core_conn, caller_set)
    processed_callers: set[str] = set()
    for record in call_records:
        caller_id = record.caller_structural_id
        if caller_id not in caller_set:
            continue
        callee_ids, _ = _resolve_callees(record.callee_identifiers, symbol_index)
        if not callee_ids or caller_id in processed_callers:
            continue
        call_hash = node_hashes.get(caller_id)
        if not call_hash:
            continue
        processed_callers.add(caller_id)
        artifact_store.upsert_node_calls(
            artifact_conn,
            caller_id=caller_id,
            callee_ids=sorted(callee_ids),
            valid=True,
            call_hash=call_hash,
        )


def _build_symbol_index(core_conn, snapshot_id: str) -> dict[str, list[str]]:
    callable_types = sorted(CALLABLE_NODE_TYPES)
    placeholders = ",".join(["?"] * len(callable_types))
    rows = core_conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
        """,
        (snapshot_id, *callable_types),
    ).fetchall()
    index: dict[str, list[str]] = defaultdict(list)
    for structural_id, node_type, qualified_name in rows:
        del node_type
        identifier = _simple_identifier(qualified_name)
        if not identifier:
            continue
        index[identifier].append(structural_id)
    return index


def _load_node_hashes(core_conn, node_ids: Iterable[str]) -> dict[str, str]:
    if not node_ids:
        return {}
    node_list = list(node_ids)
    if len(node_list) <= SQLITE_MAX_VARS:
        placeholders = ",".join("?" for _ in node_list)
        rows = core_conn.execute(
            f"""
            SELECT structural_id, content_hash
            FROM node_instances
            WHERE structural_id IN ({placeholders})
            """,
            tuple(node_list),
        ).fetchall()
        return {row[0]: row[1] for row in rows if row[1]}
    result: dict[str, str] = {}
    for batch in chunked(node_list, SQLITE_MAX_VARS):
        placeholders = ",".join("?" for _ in batch)
        rows = core_conn.execute(
            f"""
            SELECT structural_id, content_hash
            FROM node_instances
            WHERE structural_id IN ({placeholders})
            """,
            tuple(batch),
        ).fetchall()
        for row in rows:
            if row[1]:
                result[row[0]] = row[1]
    return result


def _resolve_callees(
    identifiers: Sequence[str],
    symbol_index: dict[str, Sequence[str]],
) -> tuple[set[str], set[str]]:
    resolved_ids: set[str] = set()
    resolved_names: set[str] = set()
    for identifier in identifiers:
        candidates = symbol_index.get(identifier) or []
        if len(candidates) == 1:
            resolved_ids.add(candidates[0])
            resolved_names.add(identifier)
    return resolved_ids, resolved_names


def _simple_identifier(qualified_name: str) -> str | None:
    if not qualified_name:
        return None
    parts = qualified_name.rsplit(".", 1)
    return parts[-1] if parts else qualified_name


__all__ = [
    "rebuild_graph_rollups",
    "write_call_artifacts",
]
