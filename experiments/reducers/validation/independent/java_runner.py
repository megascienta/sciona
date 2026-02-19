# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List

from .shared import CallEdge, Definition, FileParseResult, ImportEdge

SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "JavaParserRunner.java"


def _require_jar() -> str:
    jar = os.environ.get("SCIONA_JAVAPARSER_JAR")
    if not jar:
        raise RuntimeError("SCIONA_JAVAPARSER_JAR is not set")
    return jar


def parse_java_files(repo_root: Path, files: List[dict]) -> List[FileParseResult]:
    jar_path = _require_jar()
    with tempfile.TemporaryDirectory(prefix="sciona_javaparser_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        list_file = tmpdir_path / "inputs.txt"
        lines = []
        for entry in files:
            file_path = (repo_root / entry["file_path"]).resolve()
            lines.append(f"{file_path.as_posix()}\t{entry['module_qualified_name']}")
        list_file.write_text("\n".join(lines), encoding="utf-8")

        compile_result = subprocess.run(
            [
                "javac",
                "-cp",
                jar_path,
                "-d",
                tmpdir_path.as_posix(),
                SCRIPT_PATH.as_posix(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(compile_result.stderr.strip() or "javac failed")

        run_result = subprocess.run(
            [
                "java",
                "-cp",
                f"{jar_path}{os.pathsep}{tmpdir_path.as_posix()}",
                "JavaParserRunner",
                list_file.as_posix(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if run_result.returncode != 0:
            raise RuntimeError(run_result.stderr.strip() or "Java parser failed")

    data = json.loads(run_result.stdout)
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
                language=item.get("language") or "java",
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
