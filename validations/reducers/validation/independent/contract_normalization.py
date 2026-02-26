# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sciona.code_analysis.core.module_naming import module_name_from_path

from .shared import NormalizedCallEdge


def module_name_from_file(repo_root: Path, file_path: str, language: str) -> str:
    rel_path = Path(file_path)
    if language == "typescript":
        raw = module_name_from_path(
            repo_root,
            rel_path,
            strip_suffix=False,
            treat_init_as_package=False,
        )
        return normalize_ts_path(raw)
    return module_name_from_path(
        repo_root,
        rel_path,
        strip_suffix=True,
        treat_init_as_package=(language == "python"),
    )


def normalize_ts_path(path: str) -> str:
    name = path
    if name.endswith(".d.ts"):
        return name[: -len(".d.ts")]
    if name.endswith(".tsx"):
        return name[: -len(".tsx")]
    if name.endswith(".ts"):
        return name[: -len(".ts")]
    if name.endswith(".mjs"):
        return name[: -len(".mjs")]
    if name.endswith(".cjs"):
        return name[: -len(".cjs")]
    if name.endswith(".js"):
        return name[: -len(".js")]
    return name


def normalize_scoped_calls(
    calls: list[NormalizedCallEdge],
    *,
    language: str,
    module_scope: str,
) -> list[NormalizedCallEdge]:
    del language, module_scope  # Scope args keep the contract explicit for callers.
    terminal_map: dict[str, str | None] = {}
    for edge in calls:
        qname = (edge.callee_qname or "").strip()
        if "." not in qname:
            continue
        terminal = qname.rsplit(".", 1)[-1]
        existing = terminal_map.get(terminal)
        if existing is None and terminal in terminal_map:
            continue
        if existing is None:
            terminal_map[terminal] = qname
        elif existing != qname:
            terminal_map[terminal] = None
    normalized: list[NormalizedCallEdge] = []
    for edge in calls:
        qname = (edge.callee_qname or "").strip()
        callee = (edge.callee or "").strip()
        if qname and "." in qname:
            terminal = qname.rsplit(".", 1)[-1]
            mapped = terminal_map.get(terminal)
            if mapped is None and terminal in terminal_map:
                normalized.append(
                    NormalizedCallEdge(
                        caller=edge.caller,
                        callee=terminal,
                        callee_qname=None,
                        dynamic=edge.dynamic,
                        callee_text=edge.callee_text,
                    )
                )
                continue
            if mapped:
                normalized.append(
                    NormalizedCallEdge(
                        caller=edge.caller,
                        callee=mapped.rsplit(".", 1)[-1],
                        callee_qname=mapped,
                        dynamic=edge.dynamic,
                        callee_text=edge.callee_text,
                    )
                )
                continue
        elif callee:
            mapped = terminal_map.get(callee)
            if mapped:
                normalized.append(
                    NormalizedCallEdge(
                        caller=edge.caller,
                        callee=mapped.rsplit(".", 1)[-1],
                        callee_qname=mapped,
                        dynamic=edge.dynamic,
                        callee_text=edge.callee_text,
                    )
                )
                continue
        normalized.append(edge)
    return normalized


def normalization_is_scoped_consistent(calls: Iterable[NormalizedCallEdge]) -> bool:
    by_terminal: dict[str, set[str]] = {}
    for edge in calls:
        qname = (edge.callee_qname or "").strip()
        if not qname:
            continue
        terminal = qname.rsplit(".", 1)[-1]
        by_terminal.setdefault(terminal, set()).add(qname)
    return all(len(values) <= 1 for values in by_terminal.values())
