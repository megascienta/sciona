# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compact ownership and coupling summary reducer."""

from __future__ import annotations

from typing import Any

from . import dependency_edges, module_overview
from .helpers.shared.payload import render_json_payload
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="ownership_summary",
    category="coupling",
    placeholder="OWNERSHIP_SUMMARY",
    summary="Summarizes a module or package's immediate submodules, dependencies, "
    "and dependents. Use for boundary, ownership, and edit-scope triage. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    module_id: str | None = None,
    callable_id: str | None = None,
    classifier_id: str | None = None,
    top_k: int | str | None = None,
    **_: object,
) -> str:
    payload = run(
        snapshot_id,
        conn=conn,
        repo_root=repo_root,
        module_id=module_id,
        callable_id=callable_id,
        classifier_id=classifier_id,
        top_k=top_k,
    )
    return render_json_payload(payload)


def run(snapshot_id: str, **params) -> dict[str, Any]:
    conn = params.get("conn")
    repo_root = params.get("repo_root")
    module_id = params.get("module_id")
    callable_id = params.get("callable_id")
    classifier_id = params.get("classifier_id")
    top_k = _normalize_top_k(params.get("top_k"))

    overview = module_overview.run(
        snapshot_id,
        conn=conn,
        repo_root=repo_root,
        module_id=module_id,
        callable_id=callable_id,
        classifier_id=classifier_id,
        include_file_map=True,
    )
    outgoing = _load_edges(
        snapshot_id,
        conn,
        repo_root,
        module_id=overview["module_qualified_name"],
        direction="out",
    )
    incoming = _load_edges(
        snapshot_id,
        conn,
        repo_root,
        module_id=overview["module_qualified_name"],
        direction="in",
    )

    root_name = str(overview["module_qualified_name"])
    payload = {
        "projection": "ownership_summary",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "module_structural_id": overview["module_structural_id"],
        "module_qualified_name": root_name,
        "language": overview["language"],
        "file_path": overview["file_path"],
        "file_count": overview["file_count"],
        "module_file_count": overview.get("module_file_count", 0),
        "top_k": top_k,
        "submodules": _top_submodules(overview, top_k),
        "outgoing_dependencies": _bucket_edges(
            outgoing,
            root_name=root_name,
            name_field="to_module_qualified_name",
            id_field="to_module_structural_id",
            top_k=top_k,
        ),
        "incoming_dependents": _bucket_edges(
            incoming,
            root_name=root_name,
            name_field="from_module_qualified_name",
            id_field="from_module_structural_id",
            top_k=top_k,
        ),
    }
    return payload


def _normalize_top_k(top_k: int | str | None) -> int:
    if top_k is None:
        return 5
    try:
        value = int(top_k)
    except (TypeError, ValueError) as exc:
        raise ValueError("ownership_summary top_k must be an integer.") from exc
    if value <= 0:
        raise ValueError("ownership_summary top_k must be positive.")
    return min(value, 50)


def _load_edges(
    snapshot_id: str,
    conn,
    repo_root,
    *,
    module_id: str,
    direction: str,
) -> list[dict[str, Any]]:
    payload = dependency_edges.render(
        snapshot_id,
        conn,
        repo_root,
        module_id=module_id,
        direction=direction,
    )
    return list(payload.get("edges", []))


def _top_submodules(overview: dict[str, Any], top_k: int) -> dict[str, Any]:
    root_name = str(overview["module_qualified_name"])
    entries = list(overview.get("module_files", []))
    children = [
        {
            "module_structural_id": entry["module_structural_id"],
            "module_qualified_name": entry["module_qualified_name"],
            "file_path": entry["file_path"],
            "line_span": entry["line_span"],
        }
        for entry in entries
        if entry.get("module_qualified_name") != root_name
    ]
    if not children:
        children = [
            {
                "module_structural_id": overview["module_structural_id"],
                "module_qualified_name": root_name,
                "file_path": overview["file_path"],
                "line_span": overview.get("line_span"),
            }
        ]
    children.sort(
        key=lambda entry: (
            _module_depth(str(entry["module_qualified_name"])),
            str(entry["module_qualified_name"]),
        )
    )
    return {
        "count": len(children),
        "truncated": len(children) > top_k,
        "entries": children[:top_k],
    }


def _bucket_edges(
    edges: list[dict[str, Any]],
    *,
    root_name: str,
    name_field: str,
    id_field: str,
    top_k: int,
) -> dict[str, Any]:
    internal: dict[str, dict[str, Any]] = {}
    external: dict[str, dict[str, Any]] = {}
    for edge in edges:
        qualified_name = edge.get(name_field)
        if not qualified_name:
            continue
        bucket = internal if _is_internal(root_name, str(qualified_name)) else external
        entry = bucket.setdefault(
            str(qualified_name),
            {
                "module_structural_id": edge.get(id_field),
                "module_qualified_name": qualified_name,
                "edge_count": 0,
            },
        )
        entry["edge_count"] += 1
    return {
        "internal_count": len(internal),
        "external_count": len(external),
        "internal": _top_bucket_entries(internal, top_k),
        "external": _top_bucket_entries(external, top_k),
    }


def _top_bucket_entries(
    bucket: dict[str, dict[str, Any]], top_k: int
) -> dict[str, Any]:
    entries = sorted(
        bucket.values(),
        key=lambda entry: (-int(entry["edge_count"]), str(entry["module_qualified_name"])),
    )
    return {
        "count": len(entries),
        "truncated": len(entries) > top_k,
        "entries": entries[:top_k],
    }


def _is_internal(root_name: str, qualified_name: str) -> bool:
    return qualified_name == root_name or qualified_name.startswith(f"{root_name}.")


def _module_depth(qualified_name: str) -> int:
    return qualified_name.count(".")


__all__ = ["render", "run", "REDUCER_META"]
