"""Shared module naming helpers."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Sequence

from ...runtime import paths as runtime


def module_name_from_path(
    repo_root: Path,
    path: Path,
    *,
    strip_suffix: bool = True,
    treat_init_as_package: bool = False,
) -> str:
    """Compute module names from repo-relative paths without language metadata."""
    relative = path.as_posix()
    suffix = Path(relative).suffix if strip_suffix else ""
    if suffix:
        relative = _strip_suffix(relative, (suffix,))
    if treat_init_as_package:
        relative = _normalize_init_package(relative)
    clean = _normalize_module_path(relative)
    repo_prefix = runtime.repo_name_prefix(repo_root)
    result = _apply_repo_prefix(clean, repo_prefix)
    if not result:
        raise ValueError(f"Cannot determine module name for {path}")
    return result


def _strip_suffix(path_text: str, suffixes: Sequence[str]) -> str:
    for suffix in sorted(suffixes, key=len, reverse=True):
        if path_text.endswith(suffix):
            return path_text[: -len(suffix)]
    return path_text


def _normalize_init_package(path_text: str) -> str:
    path = PurePosixPath(path_text)
    if path.name != "__init__":
        return path_text
    if path.parent == PurePosixPath("."):
        return path_text
    return path.parent.as_posix()


def _normalize_module_path(path_text: str) -> str:
    if not path_text or path_text == ".":
        return ""
    return path_text.replace("/", ".")


def _apply_repo_prefix(clean: str, repo_prefix: str) -> str:
    if not repo_prefix:
        return clean
    if clean == repo_prefix or clean.startswith(f"{repo_prefix}."):
        return clean
    return f"{repo_prefix}.{clean}" if clean else repo_prefix


def _apply_package_prefix(clean: str, package_prefix: str, repo_prefix: str) -> str:
    if clean == package_prefix or clean.startswith(f"{package_prefix}."):
        clean = clean[len(package_prefix) :].lstrip(".")
    prefix = package_prefix
    if repo_prefix and prefix != repo_prefix and not prefix.startswith(f"{repo_prefix}."):
        prefix = f"{repo_prefix}.{prefix}"
    return f"{prefix}.{clean}" if clean else prefix
