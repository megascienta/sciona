"""Git repository and metadata helpers for SCIONA."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Set

from ..config import defaults
from ..errors import GitError
from .exec import git_binary, run_git, validate_git_args


def ensure_repo(repo_root: Path) -> None:
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        raise GitError(f"{repo_root} is not a git repository")
    run_git(["--version"], repo_root)


def get_repo_root(cwd: Path | None = None) -> Path:
    """Return the git repository root for the provided cwd (or current working dir)."""
    working_dir = cwd or Path.cwd()
    validate_git_args(["rev-parse", "--show-toplevel"])
    timeout = float(defaults.DEFAULT_GIT_TIMEOUT)
    try:
        result = subprocess.run(
            [git_binary(), "rev-parse", "--show-toplevel"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise GitError("SCIONA must be run inside a git repository.") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"Git command timed out: {exc}") from exc
    return Path(result.stdout.strip())


def ensure_repo_has_commits(repo_root: Path) -> None:
    """Ensure the repository has at least one commit."""
    try:
        run_git(["rev-parse", "HEAD"], repo_root)
    except GitError as exc:
        raise GitError(
            "Repository has no commits. Create an initial commit before running SCIONA."
        ) from exc


def is_worktree_dirty(repo_root: Path) -> bool:
    """Return True when the git working tree has uncommitted changes."""
    output = run_git(["status", "--porcelain"], repo_root)
    return bool(output.strip())


def worktree_status_paths(repo_root: Path) -> List[str]:
    """Return file paths reported by git status --porcelain."""
    output = run_git(["status", "--porcelain", "-z"], repo_root)
    if not output:
        return []
    paths: List[str] = []
    entries = output.split("\x00")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry or len(entry) < 4:
            continue
        status = entry[:2]
        path = entry[3:]
        if path:
            paths.append(path)
        if status and status[0] in {"R", "C"} and index < len(entries):
            renamed = entries[index]
            index += 1
            if renamed:
                paths.append(renamed)
    return paths


def diff_name_status(
    repo_root: Path,
    base_commit: str,
    *,
    cached: bool = False,
) -> List[tuple[str, List[str]]]:
    """Return parsed output for git diff --name-status base_commit."""
    args = ["diff", "--name-status"]
    if cached:
        args.append("--cached")
    args.append(base_commit)
    output = run_git(args, repo_root)
    changes: List[tuple[str, List[str]]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        paths = parts[1:]
        if not status or not paths:
            continue
        changes.append((status, paths))
    return changes


def untracked_paths(repo_root: Path) -> List[str]:
    """Return untracked file paths excluding standard ignores."""
    output = run_git(["ls-files", "--others", "--exclude-standard"], repo_root)
    return [line.strip() for line in output.splitlines() if line.strip()]


def ensure_clean_worktree(repo_root: Path) -> None:
    """Abort if the working tree contains uncommitted changes."""
    if is_worktree_dirty(repo_root):
        raise GitError(
            "Uncommitted changes detected. Please commit or stash before running SCIONA."
        )


def tracked_paths(repo_root: Path) -> Set[str]:
    ensure_repo(repo_root)
    output = run_git(["ls-files"], repo_root)
    paths = set()
    for line in output.splitlines():
        normalized = line.strip()
        if normalized:
            paths.add(Path(normalized).as_posix())
    return paths


def blob_sha(repo_root: Path, relative_path: Path) -> str:
    ensure_repo(repo_root)
    rel = relative_path.as_posix()
    return run_git(["hash-object", "--no-filters", "--", rel], repo_root)


def blob_sha_batch(repo_root: Path, relative_paths: List[Path]) -> Dict[Path, str]:
    ensure_repo(repo_root)
    if not relative_paths:
        return {}
    rel_paths = [path.as_posix() for path in relative_paths]
    for rel in rel_paths:
        if "\x00" in rel or "\n" in rel or "\r" in rel:
            raise GitError(f"Invalid path for git hash: {rel}")
    output = run_git(
        ["hash-object", "--no-filters", "--stdin-paths"],
        repo_root,
        input_text="\n".join(rel_paths),
    )
    hashes = output.splitlines()
    if len(hashes) != len(rel_paths):
        return {}
    return {Path(rel_paths[i]): hashes[i].strip() for i in range(len(rel_paths))}


def commit_meta(repo_root: Path) -> Dict[str, str]:
    ensure_repo(repo_root)
    commit_sha = run_git(["rev-parse", "HEAD"], repo_root)
    commit_time = run_git(["show", "-s", "--format=%cI", "HEAD"], repo_root)
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return {
        "git_commit_sha": commit_sha,
        "git_commit_time": commit_time,
        "git_branch": branch,
    }


__all__ = [
    "blob_sha",
    "blob_sha_batch",
    "commit_meta",
    "diff_name_status",
    "ensure_repo",
    "ensure_repo_has_commits",
    "ensure_clean_worktree",
    "get_repo_root",
    "is_worktree_dirty",
    "tracked_paths",
    "untracked_paths",
    "worktree_status_paths",
]
