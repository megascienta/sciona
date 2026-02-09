# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""User-facing SCIONA API (stable)."""

from __future__ import annotations

from ..pipelines import repo as repo_pipeline
from ..pipelines import reducers as reducers_pipeline
from ..pipelines import resolve as resolve_pipeline

init = repo_pipeline.init
build = repo_pipeline.build
status = repo_pipeline.status
init_dialog_defaults = repo_pipeline.init_dialog_defaults
init_supported_languages = repo_pipeline.init_supported_languages
init_apply_languages = repo_pipeline.init_apply_languages
clean = repo_pipeline.clean
clean_agents = repo_pipeline.clean_agents

emit = reducers_pipeline.emit
list_entries = reducers_pipeline.list_entries
get_entry = reducers_pipeline.get_entry

identifier_for_repo = resolve_pipeline.identifier_for_repo
identifier = resolve_pipeline.identifier
require_identifier = resolve_pipeline.require_identifier

__all__ = [
    "init",
    "build",
    "status",
    "init_dialog_defaults",
    "init_supported_languages",
    "init_apply_languages",
    "clean",
    "clean_agents",
    "emit",
    "list_entries",
    "get_entry",
    "identifier_for_repo",
    "identifier",
    "require_identifier",
]
