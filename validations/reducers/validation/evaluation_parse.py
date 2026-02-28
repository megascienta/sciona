# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List

from .independent.contract_normalization import module_name_from_file
from .independent.java_runner import parse_java_files
from .independent.python_ast import parse_python_files
from .independent.shared import (
    AssignmentHint,
    CallEdge,
    Definition,
    FileParseResult,
    ImportEdge,
)
from .independent.ts_node import parse_typescript_files


def _normalize_parse_result(result: FileParseResult) -> FileParseResult:
    def _dedupe_defs(values: list[Definition]) -> list[Definition]:
        seen: set[tuple[str, str, int, int]] = set()
        out: list[Definition] = []
        for item in sorted(
            values,
            key=lambda d: (d.start_line, d.end_line, d.kind, d.qualified_name),
        ):
            key = (item.kind, item.qualified_name, item.start_line, item.end_line)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _dedupe_calls(values: list[CallEdge]) -> list[CallEdge]:
        seen: set[tuple[str, str, str | None, bool, str | None]] = set()
        out: list[CallEdge] = []
        for item in sorted(
            values,
            key=lambda c: (
                c.caller,
                c.callee,
                c.callee_qname or "",
                c.dynamic,
                c.callee_text or "",
            ),
        ):
            key = (
                item.caller,
                item.callee,
                item.callee_qname,
                item.dynamic,
                item.callee_text,
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _dedupe_imports(values: list[ImportEdge]) -> list[ImportEdge]:
        seen: set[tuple[str, str, bool, str | None]] = set()
        out: list[ImportEdge] = []
        for item in sorted(
            values,
            key=lambda i: (
                i.source_module,
                i.target_module,
                i.dynamic,
                i.target_text or "",
            ),
        ):
            key = (item.source_module, item.target_module, item.dynamic, item.target_text)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    def _dedupe_hints(values: list[AssignmentHint]) -> list[AssignmentHint]:
        seen: set[tuple[str, str, str]] = set()
        out: list[AssignmentHint] = []
        for item in sorted(values, key=lambda h: (h.scope, h.receiver, h.value_text)):
            key = (item.scope, item.receiver, item.value_text)
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    result.defs = _dedupe_defs(result.defs)
    result.call_edges = _dedupe_calls(result.call_edges)
    result.import_edges = _dedupe_imports(result.import_edges)
    result.assignment_hints = _dedupe_hints(result.assignment_hints)
    return result


def parse_independent(
    repo_root: Path,
    file_entries: Dict[str, dict],
    on_file_parsed: Callable[[str], None] | None = None,
) -> Dict[str, FileParseResult]:
    by_language: Dict[str, List[dict]] = {}
    for entry in file_entries.values():
        language = str(entry.get("language") or "").lower()
        normalized_entry = dict(entry)
        file_path = str(entry.get("file_path") or "")
        if language and file_path:
            try:
                normalized_entry["module_qualified_name"] = module_name_from_file(
                    repo_root,
                    file_path,
                    language,
                )
            except Exception:
                pass
        by_language.setdefault(language, []).append(normalized_entry)

    parsers = {
        "python": parse_python_files,
        "typescript": parse_typescript_files,
        "java": parse_java_files,
    }

    results: Dict[str, FileParseResult] = {}
    for language, entries in by_language.items():
        parser = parsers.get(language)
        if not parser:
            continue
        for output in parser(repo_root, entries):
            output = _normalize_parse_result(output)
            results[output.file_path] = output
            if on_file_parsed:
                on_file_parsed(output.file_path)
    return results


def parse_independent_files(
    repo_root: Path,
    parse_file_map: Dict[str, dict],
    on_file_parsed: Callable[[str], None] | None,
) -> Dict[str, FileParseResult]:
    return parse_independent(repo_root, parse_file_map, on_file_parsed=on_file_parsed)


__all__ = ["parse_independent", "parse_independent_files"]
