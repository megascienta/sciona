"""Packaging metadata helpers (best-effort)."""
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional


@lru_cache(maxsize=4)
def _package_dir_map(repo_root: str) -> Dict[Path, str]:
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


def python_package_target(
    repo_root: Path,
    file_relative_path: Path,
) -> tuple[Optional[str], Optional[Path]]:
    """Return (package_name, package_path) owning the file based on pyproject.toml."""
    try:
        relative_path = file_relative_path.relative_to(repo_root)
    except ValueError:
        relative_path = file_relative_path
    mapping = _package_dir_map(str(repo_root.resolve()))
    if not mapping:
        return None, None
    best_name: Optional[str] = None
    best_path: Optional[Path] = None
    best_depth = -1
    for package_path, package_name in mapping.items():
        try:
            relative_path.relative_to(package_path)
        except ValueError:
            continue
        depth = len(package_path.parts)
        if depth > best_depth:
            best_name = package_name
            best_path = package_path
            best_depth = depth
    return best_name, best_path


def python_package_prefix(repo_root: Path, file_relative_path: Path) -> Optional[str]:
    """Return the package name that owns the given file, if specified in pyproject.toml."""
    package_name, _package_path = python_package_target(repo_root, file_relative_path)
    return package_name


def local_package_names(repo_root: Path) -> tuple[str, ...]:
    """Return declared local package names from pyproject.toml."""
    mapping = _package_dir_map(str(repo_root.resolve()))
    if not mapping:
        return ()
    return tuple(sorted(mapping.values()))


__all__ = [
    "python_package_target",
    "python_package_prefix",
    "local_package_names",
]
