"""Compressed system orientation reducer."""
from __future__ import annotations

from collections import Counter

from ..metadata import ReducerMeta
from ..helpers.base import load_structural_index, render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="codebase_orientation",
    scope="codebase",
    placeholders=("CODEBASE_ORIENTATION",),
    determinism="strict",
    payload_size_stats=None,
    semantic_tag="context",
    summary="Compressed codebase orientation.",
    lossy=True,
    composite=True,
)

def render(snapshot_id: str, conn, repo_root, **_: object) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="codebase_orientation reducer")
    payload = load_structural_index(snapshot_id, conn, repo_root)

    modules = payload.get("modules", {}) or {}
    module_entries = modules.get("entries", []) or []
    imports = payload.get("import_cycles", []) or []
    confidence = payload.get("confidence_summary", {}) or {}

    scale = {
        "modules": modules.get("count", len(module_entries)),
        "files": (payload.get("files") or {}).get("count"),
        "classes": (payload.get("classes") or {}).get("count"),
        "functions": (payload.get("functions") or {}).get("total"),
    }

    languages = sorted({entry.get("language") for entry in module_entries if entry.get("language")})

    pkg_counter = Counter()
    for entry in module_entries:
        name = entry.get("module_id")
        if not name:
            continue
        pkg = name.split(".", 1)[0]
        pkg_counter[pkg] += 1
    top_packages = [
        {"name": pkg, "modules": count}
        for pkg, count in pkg_counter.most_common(5)
    ]

    cycle_examples = []
    for cycle in imports[:3]:
        members = cycle.get("modules") if isinstance(cycle, dict) else None
        if members:
            cycle_examples.append(list(members)[:5])
    dependency_shape = {
        "import_cycles": {
            "count": len(imports),
            "examples": cycle_examples,
        }
    }

    summary_score = confidence.get("average_confidence")
    body = {
        "snapshot": snapshot_id,
        "languages": languages,
        "scale": scale,
        "top_packages": top_packages,
        "dependency_shape": dependency_shape,
        "confidence": {
            "summary_score": summary_score,
            "missing_file_paths": confidence.get("missing_file_paths"),
            "missing_line_spans": confidence.get("missing_line_spans"),
        },
    }

    return render_json_payload(body)
