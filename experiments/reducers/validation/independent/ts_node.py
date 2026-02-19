# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from .shared import CallEdge, Definition, FileParseResult, ImportEdge

SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "ts_parser.js"


def parse_typescript_files(repo_root: Path, files: List[dict]) -> List[FileParseResult]:
    payload_files = []
    for entry in files:
        payload_files.append(
            {
                "path": str((repo_root / entry["file_path"]).resolve()),
                "file_path": entry["file_path"],
                "module_qualified_name": entry["module_qualified_name"],
            }
        )
    payload = {"files": payload_files}
    result = subprocess.run(
        ["node", str(SCRIPT_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "TypeScript parser failed")
    data = json.loads(result.stdout)
    outputs: List[FileParseResult] = []
    for item in data.get("results", []):
        defs = []
        for entry in item.get("defs", []):
            parts = entry.split("|")
            if len(parts) != 4:
                continue
            qname, kind, start_line, end_line = parts
            defs.append(Definition(kind=kind, qualified_name=qname, start_line=int(start_line), end_line=int(end_line)))
        call_edges = []
        for entry in item.get("call_edges", []):
            parts = entry.split("|")
            if len(parts) != 4:
                continue
            caller, callee, callee_qname, dynamic = parts
            call_edges.append(
                CallEdge(
                    caller=caller,
                    callee=callee,
                    callee_qname=callee_qname or None,
                    dynamic=dynamic == "true",
                )
            )
        import_edges = []
        for entry in item.get("import_edges", []):
            parts = entry.split("|")
            if len(parts) != 3:
                continue
            src, dst, dynamic = parts
            import_edges.append(
                ImportEdge(
                    source_module=src,
                    target_module=dst,
                    dynamic=dynamic == "true",
                )
            )
        outputs.append(
            FileParseResult(
                language=item.get("language") or "typescript",
                file_path=item.get("file_path") or "",
                module_qualified_name=item.get("module_qualified_name") or "",
                defs=defs,
                call_edges=call_edges,
                import_edges=import_edges,
                parse_ok=bool(item.get("parse_ok")),
                error=item.get("error"),
            )
        )
    return outputs
