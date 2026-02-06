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
]
