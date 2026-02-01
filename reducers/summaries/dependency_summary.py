"""Compressed dependency shape reducer."""
from __future__ import annotations

from ..metadata import ReducerMeta
from ..helpers.base import load_structural_index, render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="dependency_summary",
    scope="codebase",
    placeholders=("DEPENDENCY_SUMMARY",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="dependency",
    summary="Compressed import dependency summary.",
    lossy=True,
)

def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="dependency_summary reducer")
    payload = load_structural_index(snapshot_id, conn, repo_root)
    import_cycles = payload.get("import_cycles") or []
    cycle_examples = []
    for cycle in import_cycles[:3]:
        members = cycle.get("modules") if isinstance(cycle, dict) else None
        if members:
            cycle_examples.append(list(members)[:5])

    body = {
        "import_cycles": len(import_cycles),
        "cycle_examples": cycle_examples,
    }
    return render_json_payload(body)
