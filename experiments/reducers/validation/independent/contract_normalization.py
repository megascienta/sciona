# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import importlib.util
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional

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


def normalize_python_import(
    target: str,
    module_name: str,
    is_package: bool,
    *,
    repo_prefix: str,
    local_packages: set[str],
) -> Optional[str]:
    raw = (target or "").strip()
    if not raw:
        return None
    if raw.startswith("."):
        package = _python_package_context(module_name, is_package)
        if not package:
            return None
        try:
            return importlib.util.resolve_name(raw, package)
        except ImportError:
            return None
    if repo_prefix and (raw == repo_prefix or raw.startswith(f"{repo_prefix}.")):
        return raw
    for package in local_packages:
        if raw == package or raw.startswith(f"{package}."):
            return f"{repo_prefix}.{raw}" if repo_prefix else raw
    return raw


def normalize_typescript_import(specifier: str, file_path: str, repo_root: Path) -> Optional[str]:
    spec = (specifier or "").strip().strip("'\"")
    if not spec:
        return None
    if spec.startswith("."):
        parent = PurePosixPath(Path(file_path).parent.as_posix())
        normalized = normalize_relative_path(parent, PurePosixPath(spec))
        module_path = normalize_ts_path(normalized.as_posix())
        return module_name_from_file(repo_root, module_path, "typescript")
    return spec.replace("/", ".")


def normalize_typescript_relative_index(
    specifier: str,
    file_path: str,
    repo_root: Path,
) -> Optional[str]:
    spec = (specifier or "").strip().strip("'\"")
    if not spec.startswith("."):
        return None
    parent = PurePosixPath(Path(file_path).parent.as_posix())
    normalized = normalize_relative_path(parent, PurePosixPath(spec))
    index_path = normalized / "index"
    module_path = normalize_ts_path(index_path.as_posix())
    return module_name_from_file(repo_root, module_path, "typescript")


def normalize_java_import(
    fragment: str,
    module_name: str,
    *,
    module_prefix: str | None,
    repo_prefix: str,
) -> Optional[str]:
    raw = (fragment or "").strip()
    if not raw.startswith("import"):
        return None
    is_static = raw.startswith("import static")
    text = raw[len("import") :].strip()
    if text.startswith("static"):
        text = text[len("static") :].strip()
    if text.endswith(";"):
        text = text[:-1]
    text = text.strip()
    if text.endswith(".*"):
        return None
    if not text:
        return None
    if is_static and "." in text:
        text = text.rsplit(".", 1)[0]
    if repo_prefix and (text == repo_prefix or text.startswith(f"{repo_prefix}.")):
        return text
    top_package = java_top_level_package(module_name, repo_prefix)
    if top_package and (text == top_package or text.startswith(f"{top_package}.")):
        return f"{repo_prefix}.{text}" if repo_prefix else text
    if module_prefix:
        return f"{module_prefix}.{text}"
    return text


def module_prefix_for_java_package(module_name: str, package_name: str | None) -> str | None:
    if not package_name:
        return None
    module_parts = module_name.split(".")
    package_parts = package_name.split(".")
    if len(module_parts) < len(package_parts):
        return None
    for idx in range(len(module_parts) - len(package_parts), -1, -1):
        if module_parts[idx : idx + len(package_parts)] == package_parts:
            prefix_parts = module_parts[:idx]
            return ".".join(prefix_parts) if prefix_parts else None
    return None


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


def normalize_relative_path(base: PurePosixPath, relative: PurePosixPath) -> PurePosixPath:
    parts = list(base.parts)
    for part in relative.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return PurePosixPath(*parts)


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


def java_top_level_package(module_name: str, repo_prefix: str) -> str | None:
    if repo_prefix and (
        module_name == repo_prefix or module_name.startswith(f"{repo_prefix}.")
    ):
        remainder = module_name[len(repo_prefix) + 1 :]
    else:
        remainder = module_name
    if not remainder:
        return None
    return remainder.split(".", 1)[0]


def _python_package_context(module_name: str, is_package: bool) -> str | None:
    if not module_name:
        return None
    if is_package:
        return module_name
    if "." in module_name:
        return module_name.rsplit(".", 1)[0]
    return None
