# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Repository operations API (stable)."""

from __future__ import annotations

from ..pipelines import repo as repo_pipeline

init = repo_pipeline.init
build = repo_pipeline.build
status = repo_pipeline.status
init_dialog_defaults = repo_pipeline.init_dialog_defaults
init_supported_languages = repo_pipeline.init_supported_languages
init_apply_languages = repo_pipeline.init_apply_languages
init_agents = repo_pipeline.init_agents
clean = repo_pipeline.clean
clean_agents = repo_pipeline.clean_agents
dirty_worktree_warning = repo_pipeline.dirty_worktree_warning
custom_prompts = repo_pipeline.custom_prompts
install_commit_hook = repo_pipeline.install_commit_hook
remove_commit_hook = repo_pipeline.remove_commit_hook
commit_hook_status = repo_pipeline.commit_hook_status

__all__ = [
    "init",
    "build",
    "status",
    "init_dialog_defaults",
    "init_supported_languages",
    "init_apply_languages",
    "init_agents",
    "clean",
    "clean_agents",
    "dirty_worktree_warning",
    "custom_prompts",
    "install_commit_hook",
    "remove_commit_hook",
    "commit_hook_status",
]
