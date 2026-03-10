# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json

import pytest

from sciona.pipelines.ops import setup
from sciona.runtime import constants as setup_config
from sciona.runtime.errors import (
    CorruptVersionFileError,
    NotInitializedError,
    SchemaMismatchError,
)


def test_write_and_read_version_file(tmp_path) -> None:
    sciona_dir = tmp_path / ".sciona"
    setup.write_version_file(sciona_dir)
    data = setup.read_version_file(sciona_dir)
    assert data["tool_version"] == setup_config.TOOL_VERSION
    assert data["schema_version"] == setup_config.SCHEMA_VERSION


def test_read_version_file_rejects_missing(tmp_path) -> None:
    with pytest.raises(NotInitializedError):
        setup.read_version_file(tmp_path / ".sciona")


def test_read_version_file_rejects_corrupt(tmp_path) -> None:
    sciona_dir = tmp_path / ".sciona"
    sciona_dir.mkdir()
    (sciona_dir / setup_config.VERSION_FILENAME).write_text("{not-json}")
    with pytest.raises(CorruptVersionFileError):
        setup.read_version_file(sciona_dir)


def test_ensure_schema_version_mismatch_raises(tmp_path) -> None:
    sciona_dir = tmp_path / ".sciona"
    setup.write_version_file(sciona_dir)
    data = setup.read_version_file(sciona_dir)
    data["schema_version"] = "0.0"
    with pytest.raises(SchemaMismatchError):
        setup.ensure_schema_version(data)


def test_require_initialized_requires_version_file(tmp_path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    with pytest.raises(NotInitializedError):
        setup.require_initialized(repo_root)

    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir()
    (sciona_dir / setup_config.VERSION_FILENAME).write_text(
        json.dumps({"tool_version": setup_config.TOOL_VERSION, "schema_version": setup_config.SCHEMA_VERSION}),
        encoding="utf-8",
    )
    assert setup.require_initialized(repo_root) == sciona_dir
