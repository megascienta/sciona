"""Identifier resolution helpers for prompts/reducers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .errors import WorkflowError
from .policy import repo as repo_policy
from .policy import prompt as prompt_policy
from ..data_storage.connections import core
from ..data_storage.core_db import read_ops as core_read
from ..runtime.paths import get_db_path


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
    status: str  # "exact" | "ambiguous" | "missing"
    resolved_id: Optional[str]
    candidates: tuple[ResolutionCandidate, ...]


def _resolve_identifier(
    conn,
    snapshot_id: str,
    *,
    kind: str,
    identifier: str,
    limit: int = 5,
) -> ResolutionResult:
    """Resolve an identifier to a structural_id with optional best-fit candidates."""
    node_types = _node_types_for_kind(kind)
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

    candidates = tuple(_search_candidates(conn, snapshot_id, identifier, node_types, limit=limit))
    return ResolutionResult("missing", None, candidates)


def identifier_for_repo(
    *,
    kind: str,
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
        snapshot_id = prompt_policy.resolve_latest_snapshot(conn)
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
    result = _resolve_identifier(
        conn,
        snapshot_id,
        kind=kind,
        identifier=identifier,
        limit=limit,
    )
    if result.status == "exact" and result.resolved_id:
        return result.resolved_id
    message = _format_resolution_message(kind, identifier, result)
    code = "ambiguous_node" if result.status == "ambiguous" else "missing_node"
    raise WorkflowError(message, code=code)


def _node_types_for_kind(kind: str) -> Sequence[str]:
    if kind == "callable":
        return ("function", "method")
    if kind in {"function", "method", "class", "module"}:
        return (kind,)
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
        key=lambda item: (-item.score, item.qualified_name, item.language, item.file_path)
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
    kind: str,
    identifier: str,
    result: ResolutionResult,
) -> str:
    label = kind.replace("_", " ")
    if result.status == "ambiguous":
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
    "format_resolution_message",
]


def format_resolution_message(
    kind: str,
    identifier: str,
    result: ResolutionResult,
) -> str:
    """Format a resolution message for CLI/UI use."""
    return _format_resolution_message(kind, identifier, result)


def identifier(
    conn,
    snapshot_id: str,
    *,
    kind: str,
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
