# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Packaging metadata helpers (best-effort)."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Dict


@lru_cache(maxsize=4)
def _pyproject_setuptools_block(repo_root: str) -> dict:
    repo_path = Path(repo_root)
    pyproject = repo_path / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return {}
    tool_block = data.get("tool")
    if not isinstance(tool_block, dict):
        return {}
    setuptools_block = tool_block.get("setuptools")
    if not isinstance(setuptools_block, dict):
        return {}
    return setuptools_block


@lru_cache(maxsize=4)
def _package_dir_map(repo_root: str) -> Dict[Path, str]:
    setuptools_block = _pyproject_setuptools_block(repo_root)
    if not setuptools_block:
        return {}
    package_dir = setuptools_block.get("package-dir")
    if not isinstance(package_dir, dict):
        return {}
    mapping: Dict[Path, str] = {}
    for package_name, package_path in package_dir.items():
        if not isinstance(package_name, str) or not package_name:
            continue
        if not isinstance(package_path, str) or not package_path:
            continue
        mapping[Path(package_path)] = package_name
    return mapping


@lru_cache(maxsize=4)
def _package_find_where_dirs(repo_root: str) -> tuple[Path, ...]:
    setuptools_block = _pyproject_setuptools_block(repo_root)
    if not setuptools_block:
        return ()
    packages_block = setuptools_block.get("packages")
    if not isinstance(packages_block, dict):
        return ()
    find_block = packages_block.get("find")
    if not isinstance(find_block, dict):
        return ()
    where = find_block.get("where")
    if not isinstance(where, list):
        return ()
    dirs: list[Path] = []
    for entry in where:
        if not isinstance(entry, str) or not entry:
            continue
        dirs.append(Path(entry))
    return tuple(dirs)


def _packages_from_find_where(repo_root: Path) -> tuple[str, ...]:
    discovered: set[str] = set()
    for relative_dir in _package_find_where_dirs(str(repo_root.resolve())):
        base_dir = repo_root / relative_dir
        if not base_dir.is_dir():
            continue
        for child in sorted(base_dir.iterdir()):
            if not child.is_dir():
                continue
            if (child / "__init__.py").is_file():
                discovered.add(child.name)
    return tuple(sorted(discovered))


def _module_suffix_from_path(path: Path) -> str:
    text = path.as_posix().strip("/")
    return text.replace("/", ".")


def local_package_module_roots(repo_root: Path) -> dict[str, str]:
    """Return local package names mapped to their canonical module suffix roots."""
    roots: dict[str, str] = {}
    package_dir_map = _package_dir_map(str(repo_root.resolve()))
    for package_path, package_name in package_dir_map.items():
        module_suffix = _module_suffix_from_path(package_path)
        if not module_suffix:
            continue
        roots[package_name] = module_suffix
    for relative_dir in _package_find_where_dirs(str(repo_root.resolve())):
        base_dir = repo_root / relative_dir
        if not base_dir.is_dir():
            continue
        relative_suffix = _module_suffix_from_path(relative_dir)
        for child in sorted(base_dir.iterdir()):
            if not child.is_dir():
                continue
            if not (child / "__init__.py").is_file():
                continue
            module_suffix = ".".join(
                part for part in (relative_suffix, child.name) if part
            )
            if module_suffix:
                roots.setdefault(child.name, module_suffix)
    return roots


def local_package_names(repo_root: Path) -> tuple[str, ...]:
    """Return declared local package names from pyproject.toml."""
    package_names = set(local_package_module_roots(repo_root))
    package_names.update(_packages_from_find_where(repo_root))
    if not package_names:
        return ()
    return tuple(sorted(package_names))


__all__ = [
    "local_package_module_roots",
    "local_package_names",
]
