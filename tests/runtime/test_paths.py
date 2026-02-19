# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path

import pytest

from sciona.runtime import constants as setup_config
from sciona.runtime.paths import (
    get_artifact_db_path,
    get_config_path,
    get_db_path,
    get_sciona_dir,
    repo_name_prefix,
    validate_repo_root,
)
from sciona.runtime.errors import EnvError
from tests.helpers import init_git_repo


def test_path_helpers_return_expected_locations(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    assert get_sciona_dir(repo_root) == repo_root / setup_config.SCIONA_DIR_NAME
    assert get_db_path(repo_root) == repo_root / setup_config.SCIONA_DIR_NAME / setup_config.DB_FILENAME
    assert (
        get_artifact_db_path(repo_root)
        == repo_root / setup_config.SCIONA_DIR_NAME / setup_config.ARTIFACT_DB_FILENAME
    )
    assert (
        get_config_path(repo_root)
        == repo_root / setup_config.SCIONA_DIR_NAME / setup_config.CONFIG_FILENAME
    )


def test_repo_name_prefix_sanitizes_names(tmp_path: Path) -> None:
    repo_root = tmp_path / "123 bad-name"
    repo_root.mkdir()
    prefix = repo_name_prefix(repo_root)
    assert prefix.startswith("_")
    assert "-" not in prefix


def test_validate_repo_root_requires_git_repo(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    with pytest.raises(EnvError):
        validate_repo_root(repo_root)

    init_git_repo(repo_root, commit=True)
    assert validate_repo_root(repo_root) == repo_root
