# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Internal CLI API boundary (not public)."""

from __future__ import annotations

from ..pipelines import repo as repo_pipeline
from ..pipelines import reducers as reducers_pipeline
from ..pipelines import resolve as resolve_pipeline
from ..reducers.registry import freeze_registry, get_reducers, load_reducer
from ..runtime.config import load_logging_settings, load_runtime_config
from ..runtime.logging import configure_logging, debug_enabled
from ..runtime.paths import get_repo_root, get_sciona_dir

init = repo_pipeline.init
build = repo_pipeline.build
status = repo_pipeline.status
snapshot_report = repo_pipeline.snapshot_report
init_dialog_defaults = repo_pipeline.init_dialog_defaults
init_supported_languages = repo_pipeline.init_supported_languages
init_apply_languages = repo_pipeline.init_apply_languages
init_agents = repo_pipeline.init_agents
clean = repo_pipeline.clean
clean_agents = repo_pipeline.clean_agents
dirty_worktree_warning = repo_pipeline.dirty_worktree_warning
install_commit_hook = repo_pipeline.install_commit_hook
remove_commit_hook = repo_pipeline.remove_commit_hook
commit_hook_status = repo_pipeline.commit_hook_status

emit = reducers_pipeline.emit
list_entries = reducers_pipeline.list_entries
get_entry = reducers_pipeline.get_entry

identifier_for_repo = resolve_pipeline.identifier_for_repo
identifier = resolve_pipeline.identifier
require_identifier = resolve_pipeline.require_identifier
format_resolution_message = resolve_pipeline.format_resolution_message

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
    "emit",
    "list_entries",
    "get_entry",
    "identifier_for_repo",
    "identifier",
    "require_identifier",
    "format_resolution_message",
    "freeze_registry",
    "get_reducers",
    "load_reducer",
    "configure_logging",
    "debug_enabled",
    "load_logging_settings",
    "load_runtime_config",
    "get_repo_root",
    "get_sciona_dir",
]
