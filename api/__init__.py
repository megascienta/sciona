"""Public SCIONA API surface (stable)."""
from __future__ import annotations

from ..cli.main import run
from ..cli.commands import register as register_cli_commands
from ..pipelines import repo as repo_pipeline
from ..pipelines import reducers as reducers_pipeline
from ..pipelines import resolve as resolve_pipeline
from ..runtime import addon_api
from ..runtime import addons as addon_runtime
from ..data_storage import connections as db_connections
from ..runtime import api as runtime
from ..reducers import api as reducers

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

Registry = addon_api.Registry
load = addon_runtime.load
load_for_cli = addon_runtime.load_for_cli
run_build_hooks = addon_runtime.run_build_hooks
run_inits = addon_runtime.run_inits
apply_app_hooks = addon_runtime.apply_app_hooks
apply_prompts_and_reducers = addon_runtime.apply_prompts_and_reducers
is_enabled = addon_runtime.is_enabled

core = db_connections.core
artifact = db_connections.artifact

__all__ = [
    "run",
    "register_cli_commands",
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
    "Registry",
    "load",
    "load_for_cli",
    "run_build_hooks",
    "run_inits",
    "apply_app_hooks",
    "apply_prompts_and_reducers",
    "is_enabled",
    "core",
    "artifact",
    "runtime",
    "reducers",
]
