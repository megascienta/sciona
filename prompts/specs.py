# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Prompt spec resolution helpers."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Optional
import importlib.resources as resources

PLACEHOLDER_PATTERN = re.compile(r"{([A-Za-z0-9_]+)}")


def validate_placeholder_bijection(
    template: str,
    reducer_placeholders: list[str],
    *,
    error_prefix: str = "PROMPT COMPILATION ERROR",
) -> None:
    """Ensure template placeholders are a bijection with reducer placeholders."""
    template_placeholders = PLACEHOLDER_PATTERN.findall(template)
    template_set = set(template_placeholders)
    reducer_set = set(reducer_placeholders)
    missing_placeholders = [ph for ph in reducer_placeholders if ph not in template_set]
    extra_placeholders = [ph for ph in template_set if ph not in reducer_set]
    duplicate_placeholders = sorted(
        {ph for ph in template_placeholders if template_placeholders.count(ph) > 1}
    )
    if missing_placeholders:
        raise ValueError(
            f"{error_prefix}: Missing placeholders: {', '.join(missing_placeholders)}"
        )
    if extra_placeholders:
        raise ValueError(
            f"{error_prefix}: Unmapped placeholders: {', '.join(extra_placeholders)}"
        )
    if duplicate_placeholders:
        raise ValueError(
            f"{error_prefix}: Duplicate placeholders: {', '.join(duplicate_placeholders)}"
        )


def resolve_spec_path(entry: Mapping[str, object], repo_root: Optional[Path]) -> Path:
    spec = entry.get("spec")
    if not isinstance(spec, str) or not spec:
        raise ValueError("Prompt entry is missing a spec path.")
    spec_root = entry.get("spec_root")
    if isinstance(spec_root, str) and spec_root:
        _validate_relative_path(spec_root)
    if isinstance(spec_root, str) and spec_root:
        addon_package = entry.get("_addon_package")
        if isinstance(addon_package, str) and addon_package:
            base_dir = resources.files(addon_package) / spec_root
        else:
            if repo_root is None:
                raise ValueError(
                    "Prompt specs with spec_root require a repository root."
                )
            base_dir = (repo_root / spec_root).resolve()
    elif repo_root is not None:
        from ..runtime import paths as runtime_paths

        base_dir = runtime_paths.get_prompts_dir(repo_root)
    else:
        base_dir = Path(__file__).resolve().parent / "templates"
    base_dir = Path(base_dir).resolve(strict=True)
    candidate = (base_dir / spec).resolve(strict=True)
    try:
        candidate.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError(f"Prompt spec path escapes base directory: {spec}") from exc
    _ensure_no_symlinks(candidate, base_dir)
    return candidate


def _validate_relative_path(path_value: str) -> None:
    path = PurePosixPath(path_value)
    if path.is_absolute():
        raise ValueError("Prompt spec_root must be a relative path.")
    if any(part == ".." for part in path.parts):
        raise ValueError("Prompt spec_root cannot contain '..'.")


def _ensure_no_symlinks(candidate: Path, base_dir: Path) -> None:
    current = candidate
    while True:
        if current.is_symlink():
            raise ValueError("Prompt spec paths cannot include symlinks.")
        if current == base_dir:
            break
        if current.parent == current:
            break
        current = current.parent


def load_spec_text(entry: Mapping[str, object], repo_root: Optional[Path]) -> str:
    wording = entry.get("wording")
    if isinstance(wording, str) and wording.strip():
        return wording
    path = resolve_spec_path(entry, repo_root)
    if not path.exists():
        raise FileNotFoundError(f"Unknown prompt spec '{path}'.")
    return path.read_text(encoding="utf-8")


__all__ = [
    "PLACEHOLDER_PATTERN",
    "load_spec_text",
    "resolve_spec_path",
    "validate_placeholder_bijection",
]
