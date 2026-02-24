# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from .shared import AssignmentHint, CallEdge, Definition, FileParseResult, ImportEdge

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
        cwd=str(SCRIPT_PATH.parent.parent.parent),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "TypeScript parser failed")
    data = json.loads(result.stdout)
    outputs: List[FileParseResult] = []
    for item in data.get("results", []):
        defs = []
        for entry in item.get("defs", []):
            if isinstance(entry, dict):
                qname = entry.get("qualified_name", "")
                kind = entry.get("kind", "")
                start_line = entry.get("start_line", 1)
                end_line = entry.get("end_line", start_line)
            else:
                parts = entry.split("|")
                if len(parts) != 4:
                    continue
                qname, kind, start_line, end_line = parts
            defs.append(
                Definition(
                    kind=kind,
                    qualified_name=qname,
                    start_line=int(start_line),
                    end_line=int(end_line),
                )
            )
        call_edges = []
        for entry in item.get("call_edges", []):
            if isinstance(entry, dict):
                caller = entry.get("caller", "")
                callee = entry.get("callee", "")
                callee_qname = entry.get("callee_qname")
                dynamic = entry.get("dynamic", False)
                callee_text = entry.get("callee_text")
            else:
                parts = entry.split("|")
                if len(parts) != 4:
                    continue
                caller, callee, callee_qname, dynamic = parts
                callee_text = None
            call_edges.append(
                CallEdge(
                    caller=caller,
                    callee=callee,
                    callee_qname=callee_qname or None,
                    dynamic=dynamic == "true" if isinstance(dynamic, str) else bool(dynamic),
                    callee_text=callee_text,
                )
            )
        import_edges = []
        for entry in item.get("import_edges", []):
            if isinstance(entry, dict):
                src = entry.get("source_module", "")
                dst = entry.get("target_module", "")
                dynamic = entry.get("dynamic", False)
                target_text = entry.get("target_text")
            else:
                parts = entry.split("|")
                if len(parts) != 3:
                    continue
                src, dst, dynamic = parts
                target_text = None
            import_edges.append(
                ImportEdge(
                    source_module=src,
                    target_module=dst,
                    dynamic=dynamic == "true" if isinstance(dynamic, str) else bool(dynamic),
                    target_text=target_text,
                )
            )
        assignment_hints = []
        for entry in item.get("assignment_hints", []):
            if not isinstance(entry, dict):
                continue
            scope = (entry.get("scope") or "").strip()
            receiver = (entry.get("receiver") or "").strip()
            value_text = (entry.get("value_text") or "").strip()
            if not scope or not receiver or not value_text:
                continue
            assignment_hints.append(
                AssignmentHint(scope=scope, receiver=receiver, value_text=value_text)
            )
        outputs.append(
            FileParseResult(
                language=item.get("language") or "typescript",
                file_path=item.get("file_path") or "",
                module_qualified_name=item.get("module_qualified_name") or "",
                defs=defs,
                call_edges=call_edges,
                import_edges=import_edges,
                assignment_hints=assignment_hints,
                parse_ok=bool(item.get("parse_ok")),
                error=item.get("error"),
            )
        )
    return outputs
