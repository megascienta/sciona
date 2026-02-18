# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Class relationships reducer."""

from __future__ import annotations

from ..helpers import queries
from . import class_overview
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="class_inheritance",
    category="core",
    scope="class",
    placeholders=("CLASS_INHERITANCE",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Parsed base classes and inheritance relations. " \
    "Use when reasoning about type hierarchy or polymorphic structure. " \
    "Scope: class hierarchy.",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    class_id: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="class_inheritance reducer"
    )
    resolved_id = queries.resolve_class_id(conn, snapshot_id, class_id)
    overview = class_overview.run(
        snapshot_id, conn=conn, repo_root=repo_root, class_id=resolved_id
    )
    bases = overview.get("bases") or []
    outgoing = [
        {
            "edge_type": "INHERITS",
            "related_structural_id": None,
            "related_qualified_name": base,
        }
        for base in bases
    ]
    body = {
        "class_id": resolved_id,
        "outgoing_count": len(outgoing),
        "incoming_count": 0,
        "outgoing": outgoing,
        "incoming": [],
        "edge_source": "profile" if bases else "none",
    }
    return render_json_payload(body)
