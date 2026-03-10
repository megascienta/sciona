# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI facade for repository-oriented operations."""

from __future__ import annotations

from ..pipelines.ops import repo as _repo_ops
from ..runtime.paths import get_repo_root, get_sciona_dir

init = _repo_ops.init
build = _repo_ops.build
status = _repo_ops.status
snapshot_report = _repo_ops.snapshot_report
init_dialog_defaults = _repo_ops.init_dialog_defaults
init_supported_languages = _repo_ops.init_supported_languages
init_apply_languages = _repo_ops.init_apply_languages
init_agents = _repo_ops.init_agents
clean = _repo_ops.clean
clean_agents = _repo_ops.clean_agents
dirty_worktree_warning = _repo_ops.dirty_worktree_warning
install_commit_hook = _repo_ops.install_commit_hook
remove_commit_hook = _repo_ops.remove_commit_hook
commit_hook_status = _repo_ops.commit_hook_status
__all__ = [
    "init",
    "build",
    "status",
    "snapshot_report",
    "init_dialog_defaults",
    "init_supported_languages",
    "init_apply_languages",
    "init_agents",
    "clean",
    "clean_agents",
    "dirty_worktree_warning",
    "install_commit_hook",
    "remove_commit_hook",
    "commit_hook_status",
    "get_repo_root",
    "get_sciona_dir",
]
