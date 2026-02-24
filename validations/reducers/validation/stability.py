# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

from .independent.shared import FileParseResult


def independent_results_hash(
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]],
) -> str:
    serialized: List[dict] = []
    for file_path in sorted(independent_results.keys()):
        result = independent_results[file_path]
        normalized_calls, normalized_imports = normalized_edge_map.get(file_path, ([], []))
        serialized.append(
            {
                "language": result.language,
                "file_path": result.file_path,
                "module_qualified_name": result.module_qualified_name,
                "parse_ok": result.parse_ok,
                "error": result.error,
                "defs": [
                    [definition.kind, definition.qualified_name, definition.start_line, definition.end_line]
                    for definition in result.defs
                ],
                "normalized_call_edges": [
                    [edge.caller, edge.callee, edge.callee_qname, edge.dynamic, edge.callee_text]
                    for edge in normalized_calls
                ],
                "normalized_import_edges": [
                    [edge.source_module, edge.target_module, edge.dynamic]
                    for edge in normalized_imports
                ],
            }
        )
    payload = json.dumps(serialized, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
