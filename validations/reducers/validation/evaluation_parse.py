# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List

from .independent.java_runner import parse_java_files
from .independent.python_ast import parse_python_files
from .independent.shared import FileParseResult
from .independent.ts_node import parse_typescript_files


def parse_independent(
    repo_root: Path,
    file_entries: Dict[str, dict],
    on_file_parsed: Callable[[str], None] | None = None,
) -> Dict[str, FileParseResult]:
    by_language: Dict[str, List[dict]] = {}
    for entry in file_entries.values():
        by_language.setdefault(entry["language"], []).append(entry)

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
