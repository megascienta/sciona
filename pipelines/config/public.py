"""Runtime configuration loading and repository helpers."""
from __future__ import annotations

from ...runtime import config as core_config
from ...runtime import packaging as core_packaging
from ...runtime import paths as core_paths
from .io import load_config_text, write_config_text, write_default_config


def get_config_path(repo_root):
    return core_paths.get_config_path(repo_root)


def get_db_path(repo_root):
    return core_paths.get_db_path(repo_root)


def get_artifact_db_path(repo_root):
    return core_paths.get_artifact_db_path(repo_root)


def get_repo_root():
    return core_paths.get_repo_root()


def get_sciona_dir(repo_root):
    return core_paths.get_sciona_dir(repo_root)


def get_version_file(repo_root):
    return core_paths.get_version_file(repo_root)


def python_package_prefix(repo_root, file_relative_path):
    return core_packaging.python_package_prefix(repo_root, file_relative_path)


def load_llm_settings(repo_root):
    return core_config.load_llm_settings(repo_root)


def load_language_settings(repo_root):
    return core_config.load_language_settings(repo_root)


def load_discovery_settings(repo_root):
    return core_config.load_discovery_settings(repo_root)


def load_runtime_config(repo_root):
    return core_config.load_runtime_config(repo_root)


def load_logging_settings(repo_root, *, allow_missing: bool = False):
    return core_config.load_logging_settings(repo_root, allow_missing=allow_missing)


def load_sciona_config(repo_root):
    return core_config.load_sciona_config(repo_root)


__all__ = [
    "get_config_path",
    "get_db_path",
    "get_artifact_db_path",
    "get_repo_root",
    "get_sciona_dir",
    "get_version_file",
    "load_config_text",
    "load_llm_settings",
    "load_discovery_settings",
    "load_language_settings",
    "load_logging_settings",
    "load_sciona_config",
    "load_runtime_config",
    "python_package_prefix",
    "write_config_text",
    "write_default_config",
]
