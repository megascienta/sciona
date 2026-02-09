# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Class relationships reducer."""

from __future__ import annotations

from ..helpers import queries
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="class_inheritance",
    category="structure",
    scope="class",
    placeholders=("CLASS_INHERITANCE",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="dependency",
    summary="Class inheritance and interface relationships.",
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
    queries.resolve_class_id(conn, snapshot_id, class_id)
    return render_json_payload({"outgoing": [], "incoming": []})
