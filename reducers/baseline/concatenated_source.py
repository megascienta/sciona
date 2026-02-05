"""Concatenate source reducer."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Set

from ...code_analysis.core.extract.registry import extensions_for_language
from ...code_analysis.config import LANGUAGE_CONFIG
from ...runtime import git as git_ops
from ...runtime.config import load_language_settings
from ..helpers import queries
from ...runtime.errors import ConfigError
from ..metadata import ReducerMeta
from ..helpers.base import require_connection
from ..helpers.utils import require_latest_committed_snapshot

REDUCER_META = ReducerMeta(
    reducer_id="concatenated_source",
    scope="codebase",
    placeholders=("CONCATENATED_SOURCE",),
    determinism="conditional",
    payload_size_stats=None,
    semantic_tag="context",
    summary="Concatenated source for codebase, module, or class scope.",
    lossy=True,
    baseline_only=True,
)

EXTRA_SUFFIXES = {
    ".md",
    ".rst",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".txt",
    ".j2",
    ".jinja",
    ".tmpl",
}
MAX_SOURCE_BYTES = 200_000

def render(
    snapshot_id: str,
    conn,
    repo_root,
    scope: str | None = None,
    module_id: str | None = None,
    class_id: str | None = None,
    extras: str | None = None,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(conn, snapshot_id, reducer_name="concatenated_source reducer")
    resolved_scope = _normalize_scope(scope, module_id, class_id)
    include_extras = _coerce_bool(extras)
    language_exts = _allowed_language_extensions(repo_root)
    if resolved_scope == "codebase":
        roots = queries.module_root_paths(conn, snapshot_id, repo_root)
    elif resolved_scope == "module":
        roots = [queries.resolve_module_root(conn, snapshot_id, module_id, repo_root)]
    else:
        roots = [_resolve_class_root(conn, snapshot_id, class_id, repo_root)]
    file_paths = _collect_paths(repo_root, roots, include_extras, language_exts)
    return _render_file_dump(repo_root, file_paths)

def _normalize_scope(scope: str | None, module_id: str | None, class_id: str | None) -> str:
    if scope is None:
        raise ValueError("concatenated_source_v1 requires a scope.")
    normalized = scope.strip().lower()
    if normalized not in {"codebase", "module", "class"}:
        raise ValueError("concatenated_source_v1 scope must be 'codebase', 'module', or 'class'.")
    if normalized == "module" and not module_id:
        raise ValueError("concatenated_source_v1 scope 'module' requires module_id.")
    if normalized == "class" and not class_id:
        raise ValueError("concatenated_source_v1 scope 'class' requires class_id.")
    if normalized == "codebase" and module_id:
        raise ValueError("concatenated_source_v1 scope 'codebase' must not include module_id.")
    if normalized == "codebase" and class_id:
        raise ValueError("concatenated_source_v1 scope 'codebase' must not include class_id.")
    if normalized == "module" and class_id:
        raise ValueError("concatenated_source_v1 scope 'module' must not include class_id.")
    return normalized

def _resolve_class_root(conn, snapshot_id: str, class_id: str, repo_root: Path) -> Path:
    structural_id = queries.resolve_class_id(conn, snapshot_id, class_id)
    row = conn.execute(
        """
        SELECT ni.file_path
        FROM node_instances ni
        WHERE ni.snapshot_id = ?
          AND ni.structural_id = ?
        LIMIT 1
        """,
        (snapshot_id, structural_id),
    ).fetchone()
    if not row or not row["file_path"]:
        raise ValueError(f"Class '{class_id}' missing file_path in snapshot '{snapshot_id}'.")
    file_path = Path(row["file_path"])
    if file_path.is_absolute():
        try:
            return file_path.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(f"Path '{file_path}' is outside the repo root.") from exc
    return Path(file_path.as_posix())

def _collect_paths(
    repo_root: Path,
    roots: Iterable[Path],
    include_extras: bool,
    language_exts: Set[str],
) -> List[Path]:
    tracked = git_ops.tracked_paths(repo_root)
    tracked_paths = {Path(path) for path in tracked}
    root_list = list(roots)
    base = [
        rel_path
        for rel_path in tracked_paths
        if _is_under_any_root(rel_path, root_list)
        and _is_language_file(rel_path, language_exts)
        and (repo_root / rel_path).exists()
    ]
    extra_paths: Set[Path] = set()
    if include_extras:
        extra_paths = _collect_extra_paths(repo_root, root_list)
    combined = set(base) | extra_paths
    return sorted(combined, key=lambda path: path.as_posix())

def _collect_extra_paths(
    repo_root: Path,
    roots: Iterable[Path],
) -> Set[Path]:
    extras: Set[Path] = set()
    for root in roots:
        root_path = repo_root / root
        if not root_path.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [name for name in dirnames if name not in {".git", ".sciona"}]
            for filename in filenames:
                path = Path(dirpath) / filename
                rel_path = path.relative_to(repo_root)
                if path.suffix.lower() not in EXTRA_SUFFIXES:
                    continue
                extras.add(rel_path)
    return extras

def _is_under_any_root(path: Path, roots: Iterable[Path]) -> bool:
    return any(path.is_relative_to(root) for root in roots)

def _is_language_file(path: Path, language_exts: Set[str]) -> bool:
    return path.suffix.lower() in language_exts

def _allowed_language_extensions(repo_root: Path) -> Set[str]:
    try:
        settings = load_language_settings(repo_root)
    except ConfigError:
        return _all_language_extensions()
    extensions: Set[str] = set()
    for name, lang_settings in settings.items():
        if not lang_settings.enabled:
            continue
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions

def _all_language_extensions() -> Set[str]:
    extensions: Set[str] = set()
    for name in LANGUAGE_CONFIG:
        extensions.update(ext.lower() for ext in extensions_for_language(name))
    return extensions

def _coerce_bool(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value '{value}'.")

def _render_file_dump(repo_root: Path, relative_paths: Iterable[Path]) -> str:
    chunks: List[str] = []
    for rel_path in relative_paths:
        header = rel_path.as_posix()
        chunks.append(f"# {header}\n\n")
        path = repo_root / rel_path
        try:
            file_size = path.stat().st_size
        except FileNotFoundError:
            chunks.append(f"# MISSING: {header}\n\n")
            continue
        if file_size > MAX_SOURCE_BYTES:
            chunks.append(f"# SKIPPED: {header} (too large)\n\n")
            continue
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            chunks.append(f"# MISSING: {header}\n\n")
            continue
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            chunks.append(f"# SKIPPED: {header} (non-UTF-8)\n\n")
            continue
        chunks.append(content)
        if not content.endswith("\n"):
            chunks.append("\n")
        chunks.append("\n")
    return "".join(chunks)

__all__ = ["EXTRA_SUFFIXES"]
