# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Low-level git process execution + argument validation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Set

from .. import config as runtime_config
from ..config import defaults
from ..errors import GitError

_GIT_BIN: str | None = None


def resolve_git_timeout(repo_root: Path | None) -> float:
    env_override = os.getenv("SCIONA_GIT_TIMEOUT")
    if env_override:
        try:
            return float(env_override)
        except ValueError:
            pass
    if repo_root is not None:
        try:
            settings = runtime_config.load_runtime_config(repo_root).git
            if settings.timeout > 0:
                return float(settings.timeout)
        except Exception:
            pass
    return float(defaults.DEFAULT_GIT_TIMEOUT)


def git_binary() -> str:
    global _GIT_BIN
    if _GIT_BIN is None:
        _GIT_BIN = shutil.which("git")
    if not _GIT_BIN:
        raise GitError("git command not available")
    return _GIT_BIN


def _run_git_raw(
    args: list[str],
    *,
    cwd: Path,
    timeout: float,
    input_text: str | None = None,
) -> str:
    try:
        result = subprocess.run(
            [git_binary(), *[str(arg) for arg in args]],
            cwd=cwd,
            input=input_text,
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


def validate_repo_root(repo_root: Path) -> Path:
    try:
        resolved = repo_root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise GitError(f"Invalid repo path: {repo_root}") from exc
    if not resolved.is_dir():
        raise GitError(f"Invalid repo path: {resolved}")
    validate_git_args(["rev-parse", "--git-dir"])
    try:
        _run_git_raw(
            ["rev-parse", "--git-dir"],
            cwd=resolved,
            timeout=resolve_git_timeout(resolved),
        )
    except GitError as exc:
        if str(exc) == "git command not available":
            raise
        raise GitError(f"{resolved} is not a git repository") from exc
    return resolved


def validate_git_args(args: list[str]) -> None:
    if not args:
        raise GitError("Missing git arguments.")
    for arg in args:
        text = str(arg)
        if "\x00" in text or "\n" in text or "\r" in text:
            raise GitError(f"Invalid git argument: {arg}")
    if args[0] == "--version":
        if len(args) > 1:
            raise GitError("Unexpected arguments for git --version.")
        return
    command = str(args[0])
    allowed_options: dict[str, Set[str]] = {
        "diff": {"--name-status", "--cached", "-M", "-C"},
        "hash-object": {"--no-filters", "--stdin-paths"},
        "merge-base": set(),
        "rev-parse": {"--abbrev-ref", "--show-toplevel", "--git-dir"},
        "show": {"-s", "--format=%cI"},
        "status": {"--porcelain", "-z"},
        "ls-files": {"--others", "--exclude-standard", "--stage", "-c", "-i", "-ci"},
    }
    if command not in allowed_options:
        raise GitError(f"Unsupported git command: {command}")
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


def run_git(
    args: list[str],
    repo_root: Path,
    *,
    timeout: float | None = None,
    input_text: str | None = None,
) -> str:
    repo_root = validate_repo_root(repo_root)
    validate_git_args(args)
    timeout = resolve_git_timeout(repo_root) if timeout is None else timeout
    return _run_git_raw(
        args,
        cwd=repo_root,
        timeout=timeout,
        input_text=input_text,
    )


def run_git_in_cwd(
    args: list[str],
    cwd: Path,
    *,
    timeout: float | None = None,
    input_text: str | None = None,
) -> str:
    validate_git_args(args)
    timeout = resolve_git_timeout(None) if timeout is None else timeout
    return _run_git_raw(
        args,
        cwd=cwd,
        timeout=timeout,
        input_text=input_text,
    )


__all__ = [
    "git_binary",
    "resolve_git_timeout",
    "run_git_in_cwd",
    "run_git",
    "validate_git_args",
    "validate_repo_root",
]
