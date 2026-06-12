# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Identifier resolution helpers for reducers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from ..errors import WorkflowError
from ..policy import repo as repo_policy
from ..policy import snapshot as snapshot_policy
from ...code_analysis.config import LANGUAGE_CONFIG
from ...data_storage.connections import core
from ...data_storage.core_db import read_ops as core_read
from ...runtime.paths import get_db_path

_LANGUAGE_PREFIXES = frozenset(LANGUAGE_CONFIG)

_ALL_NODE_TYPES = ("callable", "classifier", "module")

# Admits prefix (0.9) and suffix (0.8) matches: the identifier must be a
# complete head or tail of the qualified name to auto-resolve.
_AUTO_RESOLVE_THRESHOLD = 0.8


@dataclass(frozen=True)
class ResolutionCandidate:
    structural_id: str
    node_type: str
    language: str
    qualified_name: str
    file_path: str
    score: float


@dataclass(frozen=True)
class ResolutionResult:
    status: str  # "exact" | "resolved" | "ambiguous" | "missing"
    resolved_id: Optional[str]
    candidates: tuple[ResolutionCandidate, ...]
    resolved_from: Optional[str] = None  # original input when auto-resolved


def _resolve_identifier(
    conn,
    snapshot_id: str,
    *,
    kind: Optional[str],
    identifier: str,
    limit: int = 5,
) -> ResolutionResult:
    """Resolve an identifier to a structural_id with optional best-fit candidates."""
    node_types = _node_types_for_kind(kind)
    requested = identifier
    language, identifier = _split_language_prefix(identifier)
    if not identifier:
        return ResolutionResult("missing", None, tuple())

    exact = _lookup_structural_id(conn, snapshot_id, identifier, node_types)
    if exact is not None:
        candidate = ResolutionCandidate(
            structural_id=exact["structural_id"],
            node_type=exact["node_type"],
            language=exact["language"],
            qualified_name=exact["qualified_name"],
            file_path=exact["file_path"],
            score=1.0,
        )
        return ResolutionResult("exact", exact["structural_id"], (candidate,))

    matches = _lookup_by_qualified_name(conn, snapshot_id, identifier, node_types)
    if language is not None and len(matches) > 1:
        language_matches = [
            match for match in matches if match["language"] == language
        ]
        if language_matches:
            matches = language_matches
    if len(matches) == 1:
        match = matches[0]
        candidate = ResolutionCandidate(
            structural_id=match["structural_id"],
            node_type=match["node_type"],
            language=match["language"],
            qualified_name=match["qualified_name"],
            file_path=match["file_path"],
            score=1.0,
        )
        return ResolutionResult("exact", match["structural_id"], (candidate,))
    if len(matches) > 1:
        candidates = tuple(
            ResolutionCandidate(
                structural_id=match["structural_id"],
                node_type=match["node_type"],
                language=match["language"],
                qualified_name=match["qualified_name"],
                file_path=match["file_path"],
                score=1.0,
            )
            for match in matches
        )
        return ResolutionResult("ambiguous", None, candidates)

    candidates = tuple(
        _search_candidates(conn, snapshot_id, identifier, node_types, limit=limit)
    )
    if not candidates:
        return ResolutionResult("missing", None, tuple())
    cleared = [
        candidate
        for candidate in candidates
        if candidate.score >= _AUTO_RESOLVE_THRESHOLD
        and (language is None or candidate.language == language)
    ]
    if len(cleared) == 1:
        return ResolutionResult(
            "resolved",
            cleared[0].structural_id,
            candidates,
            resolved_from=requested,
        )
    return ResolutionResult("ambiguous", None, candidates)


def identifier_for_repo(
    *,
    kind: Optional[str],
    identifier: str,
    repo_root: Optional[Path] = None,
    limit: int = 5,
) -> ResolutionResult:
    """Resolve an identifier using repo preconditions and latest snapshot."""
    repo_state = repo_policy.resolve_repo_state(repo_root, allow_missing_config=True)
    repo_policy.ensure_initialized(repo_state)
    db_path = get_db_path(repo_state.repo_root)
    if not db_path.exists():
        raise WorkflowError(
            "No committed snapshots available. Run 'sciona build' first.",
            code="missing_snapshot",
        )
    with core(db_path, repo_root=repo_state.repo_root) as conn:
        snapshot_id = snapshot_policy.resolve_latest_snapshot(conn)
        return _resolve_identifier(
            conn,
            snapshot_id,
            kind=kind,
            identifier=identifier,
            limit=limit,
        )


def require_identifier(
    conn,
    snapshot_id: str,
    *,
    kind: str,
    identifier: str,
    limit: int = 5,
) -> str:
    result = require_identifier_result(
        conn,
        snapshot_id,
        kind=kind,
        identifier=identifier,
        limit=limit,
    )
    return result.resolved_id


def require_identifier_result(
    conn,
    snapshot_id: str,
    *,
    kind: str,
    identifier: str,
    limit: int = 5,
) -> ResolutionResult:
    """Resolve an identifier or raise; returns the full resolution result."""
    result = _resolve_identifier(
        conn,
        snapshot_id,
        kind=kind,
        identifier=identifier,
        limit=limit,
    )
    if result.status in ("exact", "resolved") and result.resolved_id:
        return result
    message = _format_resolution_message(kind, identifier, result)
    code = "ambiguous_node" if result.status == "ambiguous" else "missing_node"
    raise WorkflowError(message, code=code)


def _split_language_prefix(identifier: str) -> tuple[Optional[str], str]:
    """Split a printed '<language>:' prefix off an identifier, if present."""
    prefix, sep, remainder = identifier.partition(":")
    if sep and prefix.lower() in _LANGUAGE_PREFIXES:
        return prefix.lower(), remainder
    return None, identifier


def _node_types_for_kind(kind: Optional[str]) -> Sequence[str]:
    if kind is None:
        return _ALL_NODE_TYPES
    normalized = str(kind).strip().lower()
    if normalized in {"any", "all"}:
        return _ALL_NODE_TYPES
    if normalized in {"callable", "function", "method"}:
        return ("callable",)
    if normalized in {"classifier", "class", "type"}:
        return ("classifier",)
    if normalized == "module":
        return ("module",)
    raise ValueError(f"Unknown identifier kind '{kind}'.")


def _lookup_structural_id(
    conn,
    snapshot_id: str,
    identifier: str,
    node_types: Sequence[str],
) -> Optional[dict[str, str]]:
    return core_read.lookup_structural_id(conn, snapshot_id, identifier, node_types)


def _lookup_by_qualified_name(
    conn,
    snapshot_id: str,
    identifier: str,
    node_types: Sequence[str],
) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for node_type in node_types:
        matches.extend(
            core_read.lookup_node_instances(
                conn,
                snapshot_id=snapshot_id,
                node_type=node_type,
                qualified_name=identifier,
            )
        )
    return matches


def _search_candidates(
    conn,
    snapshot_id: str,
    identifier: str,
    node_types: Sequence[str],
    *,
    limit: int = 5,
) -> Iterable[ResolutionCandidate]:
    lowered = identifier.lower()
    rows = core_read.search_node_instances(
        conn,
        snapshot_id,
        node_types,
        identifier,
        limit=limit,
    )
    candidates: list[ResolutionCandidate] = []
    for row in rows:
        score = _score_identifier(lowered, str(row["qualified_name"]).lower())
        candidates.append(
            ResolutionCandidate(
                structural_id=row["structural_id"],
                node_type=row["node_type"],
                language=row["language"],
                qualified_name=row["qualified_name"],
                file_path=row["file_path"],
                score=score,
            )
        )
    candidates.sort(
        key=lambda item: (
            -item.score,
            item.qualified_name,
            item.language,
            item.file_path,
        )
    )
    return candidates[:limit]


def _score_identifier(identifier: str, qualified_name: str) -> float:
    if identifier == qualified_name:
        return 1.0
    if qualified_name.startswith(identifier):
        return 0.9
    if qualified_name.endswith(identifier):
        return 0.8
    if f".{identifier}" in qualified_name:
        return 0.75
    if identifier in qualified_name:
        return 0.6
    return 0.5


def _format_resolution_message(
    kind: Optional[str],
    identifier: str,
    result: ResolutionResult,
) -> str:
    label = kind.replace("_", " ") if kind else "identifier"
    if result.status == "ambiguous" and all(
        candidate.score == 1.0 for candidate in result.candidates
    ):
        lines = [f"Multiple matches found for {label} '{identifier}':"]
    elif result.candidates:
        lines = [f"No exact match found for {label} '{identifier}'. Best matches:"]
    else:
        return f"No matches found for {label} '{identifier}'."
    lines.extend(_format_candidates(result.candidates))
    lines.append("Please disambiguate or use --id.")
    return "\n".join(lines)


def _format_candidates(candidates: Iterable[ResolutionCandidate]) -> list[str]:
    lines: list[str] = []
    for candidate in candidates:
        lines.append(
            "  - "
            f"{candidate.language}:{candidate.qualified_name} "
            f"(file: {candidate.file_path}) "
            f"[id: {candidate.structural_id}]"
        )
    return lines


__all__ = [
    "ResolutionCandidate",
    "ResolutionResult",
    "identifier_for_repo",
    "identifier",
    "require_identifier",
    "require_identifier_result",
    "format_resolution_message",
]


def format_resolution_message(
    kind: Optional[str],
    identifier: str,
    result: ResolutionResult,
) -> str:
    """Format a resolution message for CLI/UI use."""
    return _format_resolution_message(kind, identifier, result)


def identifier(
    conn,
    snapshot_id: str,
    *,
    kind: Optional[str],
    identifier: str,
    limit: int = 5,
) -> ResolutionResult:
    """Resolve an identifier to a structural_id with optional best-fit candidates."""
    return _resolve_identifier(
        conn,
        snapshot_id,
        kind=kind,
        identifier=identifier,
        limit=limit,
    )
