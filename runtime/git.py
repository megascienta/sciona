"""Git helper utilities for SCIONA."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from .errors import GitError
from . import config as runtime_config
from . import config_defaults as defaults

_GIT_BIN: str | None = None


def _resolve_git_timeout(repo_root: Path) -> float:
    env_override = os.getenv("SCIONA_GIT_TIMEOUT")
    if env_override:
        try:
            return float(env_override)
        except ValueError:
            pass
    try:
        settings = runtime_config.load_runtime_config(repo_root).git
        if settings.timeout > 0:
            return float(settings.timeout)
    except Exception:
        pass
    return float(defaults.DEFAULT_GIT_TIMEOUT)


@dataclass(frozen=True)
class RenameRecord:
    old_path: Path
    new_path: Path
    similarity: float


def _git_binary() -> str:
    global _GIT_BIN
    if _GIT_BIN is None:
        _GIT_BIN = shutil.which("git")
    if not _GIT_BIN:
        raise GitError("git command not available")
    return _GIT_BIN


def run_git(args: list[str], repo_root: Path, *, timeout: float | None = None) -> str:
    repo_root = _validate_repo_root(repo_root)
    _validate_git_args(args)
    timeout = _resolve_git_timeout(repo_root) if timeout is None else timeout
    try:
        result = subprocess.run(
            [_git_binary(), *[str(arg) for arg in args]],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(f"Git command failed: {exc.stderr.strip() or exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"Git command timed out: {exc}") from exc
    return result.stdout.strip()


def _validate_repo_root(repo_root: Path) -> Path:
    try:
        resolved = repo_root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise GitError(f"Invalid repo path: {repo_root}") from exc
    if not resolved.is_dir():
        raise GitError(f"Invalid repo path: {resolved}")
    if not (resolved / ".git").exists():
        raise GitError(f"{resolved} is not a git repository")
    return resolved


def _validate_git_args(args: list[str]) -> None:
    if not args:
        raise GitError("Missing git arguments.")
    dangerous_chars = {
        ";",
        "|",
        "&",
        "`",
        "$",
        "(",
        ")",
        "<",
        ">",
        "*",
        "?",
        "[",
        "]",
        "{",
        "}",
        "\\",
        "'",
        "\"",
    }
    for arg in args:
        text = str(arg)
        if "\x00" in text or "\n" in text or "\r" in text or "\t" in text:
            raise GitError(f"Invalid git argument: {arg}")
        if any(char in text for char in dangerous_chars):
            raise GitError(f"Invalid git argument: {arg}")
    if args[0] == "--version":
        return
    command = str(args[0])
    allowed_options: dict[str, Set[str]] = {
        "hash-object": {"--no-filters", "--stdin-paths"},
        "rev-parse": {"--abbrev-ref", "--show-toplevel"},
        "show": {"-s", "--format=%cI"},
        "rev-list": {"--max-count=", "--since"},
        "worktree": {"--force", "--detach"},
        "checkout": {"--detach"},
        "diff": {"--name-status", "-M"},
        "status": {"--porcelain", "-z"},
        "ls-files": set(),
    }
    allowed = allowed_options.get(command, set())
    allow_dash_args = False
    for arg in args[1:]:
        text = str(arg)
        if text == "--":
            allow_dash_args = True
            continue
        if text.startswith("-") and not allow_dash_args:
            if any(text == opt or text.startswith(opt) for opt in allowed):
                continue
            raise GitError(f"Refusing unsafe git argument without '--': {arg}")


def ensure_repo(repo_root: Path) -> None:
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        raise GitError(f"{repo_root} is not a git repository")
    run_git(["--version"], repo_root)


def get_repo_root(cwd: Path | None = None) -> Path:
    """Return the git repository root for the provided cwd (or current working dir)."""
    working_dir = cwd or Path.cwd()
    _validate_git_args(["rev-parse", "--show-toplevel"])
    timeout = float(defaults.DEFAULT_GIT_TIMEOUT)
    try:
        result = subprocess.run(
            [_git_binary(), "rev-parse", "--show-toplevel"],
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


def ensure_clean_worktree(repo_root: Path) -> None:
    """Abort if the working tree contains uncommitted changes."""
    if is_worktree_dirty(repo_root):
        raise GitError("Uncommitted changes detected. Please commit or stash before running SCIONA.")


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
    timeout = _resolve_git_timeout(repo_root)
    try:
        result = subprocess.run(
            [_git_binary(), "hash-object", "--no-filters", "--stdin-paths"],
            cwd=repo_root,
            input="\n".join(rel_paths),
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(f"Failed to hash files: {exc.stderr.strip() or exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"Git command timed out: {exc}") from exc
    hashes = result.stdout.splitlines()
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


def list_commits(repo_root: Path, limit: int, since_days: Optional[int]) -> List[str]:
    ensure_repo(repo_root)
    limit = max(1, limit)
    args = ["rev-list", f"--max-count={limit}", "HEAD"]
    if since_days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
        args.extend(["--since", cutoff])
    output = run_git(args, repo_root)
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    commits.reverse()
    head_sha = run_git(["rev-parse", "HEAD"], repo_root)
    if not commits:
        return [head_sha]
    if commits[-1] != head_sha:
        commits.append(head_sha)
    return commits


def worktree_add(repo_root: Path, path: Path) -> None:
    ensure_repo(repo_root)
    run_git(["worktree", "add", "--force", "--detach", "--", str(path), "HEAD"], repo_root)


def worktree_remove(repo_root: Path, path: Path) -> None:
    ensure_repo(repo_root)
    run_git(["worktree", "remove", "--force", "--", str(path)], repo_root)


def checkout_detached(repo_root: Path, commit: str) -> None:
    ensure_repo(repo_root)
    run_git(["checkout", "--detach", commit], repo_root)


__all__ = [
    "GitError",
    "RenameRecord",
    "blob_sha",
    "blob_sha_batch",
    "checkout_detached",
    "commit_meta",
    "ensure_repo",
    "ensure_repo_has_commits",
    "ensure_clean_worktree",
    "get_repo_root",
    "is_worktree_dirty",
    "list_commits",
    "run_git",
    "tracked_paths",
    "worktree_status_paths",
    "worktree_add",
    "worktree_remove",
]
