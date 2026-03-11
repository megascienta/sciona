# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Source-file helpers shared by reducers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from ....runtime.common.text import canonical_span_text


def line_span_hash(
    repo_root: Optional[Path],
    file_path: Optional[str],
    line_span: Optional[list[int]],
) -> Optional[str]:
    if repo_root is None or not file_path or not line_span:
        return None
    if len(line_span) != 2:
        return None
    start, end = line_span
    if start is None or end is None or start < 1 or end < start:
        return None
    resolved = resolve_repo_file(repo_root, file_path)
    if resolved is None:
        return None
    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = content.splitlines(keepends=True)
    if start > len(lines):
        return None
    segment = "".join(lines[start - 1 : min(end, len(lines))])
    if not segment:
        return None
    canonical = canonical_span_text(segment)
    if not canonical:
        return None
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def resolve_repo_file(
    repo_root: Optional[Path],
    file_path: Optional[str | Path],
) -> Optional[Path]:
    if repo_root is None or not file_path:
        return None
    repo_root = Path(repo_root).resolve()
    candidate = Path(file_path)
    if candidate.is_absolute():
        full_path = candidate
    else:
        full_path = repo_root / candidate
    try:
        resolved = full_path.resolve()
    except FileNotFoundError:
        return None
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None
    if not resolved.is_file():
        return None
    return resolved


__all__ = ["line_span_hash", "resolve_repo_file"]
