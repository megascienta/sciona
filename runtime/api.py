"""Addon-facing runtime API (stable facade)."""
from __future__ import annotations

from ..cli.utils import cli_call
from ..pipelines.config import public as config
from ..pipelines.errors import WorkflowError
from ..pipelines.policy import repo as repo_policy
from ..pipelines.policy import prompt as prompt_policy
from ..pipelines.prompt import compile_prompt_by_name
from ..pipelines.progress import ProgressFactory
from ..runtime.llm import Adapter
from ..runtime.time import utc_now
from ..runtime.errors import ConfigError
from ..runtime.config_defaults import DEFAULT_DB_TIMEOUT
from ..runtime.addon_api import Registry
from ..runtime.addons import apply_prompts_and_reducers, is_enabled
from ..data_storage.connections import core, artifact
from ..data_storage.encoding import bool_to_int, int_to_bool
from ..data_storage.sql_utils import SQLITE_MAX_VARS, chunked, temp_id_table
from ..data_storage.transactions import transaction

get_db_path = config.get_db_path
get_artifact_db_path = config.get_artifact_db_path
get_config_path = config.get_config_path
get_sciona_dir = config.get_sciona_dir
load_llm_settings = config.load_llm_settings
load_runtime_config = config.load_runtime_config


def get_repo_root():
    return config.get_repo_root()

__all__ = [
    "Adapter",
    "ProgressFactory",
    "WorkflowError",
    "ConfigError",
    "DEFAULT_DB_TIMEOUT",
    "Registry",
    "apply_prompts_and_reducers",
    "is_enabled",
    "repo_policy",
    "prompt_policy",
    "compile_prompt_by_name",
    "cli_call",
    "utc_now",
    "transaction",
    "temp_id_table",
    "chunked",
    "SQLITE_MAX_VARS",
    "bool_to_int",
    "int_to_bool",
    "core",
    "artifact",
    "get_repo_root",
    "get_db_path",
    "get_artifact_db_path",
    "get_config_path",
    "get_sciona_dir",
    "load_llm_settings",
    "load_runtime_config",
]
