# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Import migration impact reducer."""

from __future__ import annotations

from typing import Any

from .helpers.shared.render import render_json_payload
from .metadata import ReducerMeta
from .ownership_summary import run as ownership_run

REDUCER_META = ReducerMeta(
    reducer_id="import_migration_impact",
    category="coupling",
    placeholder="IMPORT_MIGRATION_IMPACT",
    summary="Migration-oriented import impact summary for a module or package. "
    "Highlights importers, dependencies, and wrapper pressure. ",
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
):
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
    ownership = ownership_run(snapshot_id, **params)
    importers = ownership["incoming_dependents"]
    dependencies = ownership["outgoing_dependencies"]

    external_importers = importers["external"]["count"]
    internal_importers = importers["internal"]["count"]
    external_dependencies = dependencies["external"]["count"]
    internal_dependencies = dependencies["internal"]["count"]
    total_importers = external_importers + internal_importers
    total_dependencies = external_dependencies + internal_dependencies

    return {
        "projection": "import_migration_impact",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "module_structural_id": ownership["module_structural_id"],
        "module_qualified_name": ownership["module_qualified_name"],
        "language": ownership["language"],
        "top_k": ownership["top_k"],
        "direct_importers": importers,
        "direct_dependencies": dependencies,
        "likely_break_surfaces": _break_surfaces(importers, ownership["top_k"]),
        "likely_update_targets": _break_surfaces(dependencies, ownership["top_k"]),
        "migration_signals": {
            "total_importer_groups": total_importers,
            "total_dependency_groups": total_dependencies,
            "external_importers_present": external_importers > 0,
            "internal_importers_present": internal_importers > 0,
            "external_dependencies_present": external_dependencies > 0,
            "internal_dependencies_present": internal_dependencies > 0,
            "compatibility_wrappers_recommended": external_importers > 0,
            "direct_rewrite_feasible": external_importers == 0,
        },
    }


def _break_surfaces(bucketed: dict[str, Any], top_k: int) -> dict[str, Any]:
    external_entries = list(bucketed["external"]["entries"])
    internal_entries = list(bucketed["internal"]["entries"])
    ordered = [*external_entries, *internal_entries]
    return {
        "count": len(ordered),
        "truncated": len(ordered) > top_k,
        "entries": ordered[:top_k],
    }


__all__ = ["render", "run", "REDUCER_META"]
