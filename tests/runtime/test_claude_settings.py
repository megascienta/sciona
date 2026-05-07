# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json
from pathlib import Path

import pytest

from sciona.runtime.agents import settings_setup as settings


def _settings_path(repo_root: Path) -> Path:
    return repo_root / settings.CLAUDE_DIR / settings.SETTINGS_FILENAME


def test_upsert_creates_settings_file(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    path = settings.upsert_claude_settings(tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    allow = data["permissions"]["allow"]
    assert any(e.startswith(settings.SCIONA_MARKER) for e in allow)


def test_upsert_injects_all_expected_permissions(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    settings.upsert_claude_settings(tmp_path)
    data = json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))
    allow = data["permissions"]["allow"]
    sciona_entries = [e[len(settings.SCIONA_MARKER):].strip() for e in allow if e.startswith(settings.SCIONA_MARKER)]
    for expected in settings.SCIONA_PERMISSIONS:
        assert expected in sciona_entries, f"Missing permission: {expected}"


def test_upsert_creates_dot_claude_dir_if_absent(tmp_path: Path) -> None:
    assert not (tmp_path / settings.CLAUDE_DIR).exists()
    settings.upsert_claude_settings(tmp_path)
    assert _settings_path(tmp_path).exists()


def test_upsert_preserves_existing_non_sciona_content(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    existing = {"permissions": {"allow": ["Bash(git status)"]}, "effortLevel": "medium"}
    target.write_text(json.dumps(existing), encoding="utf-8")

    settings.upsert_claude_settings(tmp_path)
    data = json.loads(target.read_text(encoding="utf-8"))

    assert "Bash(git status)" in data["permissions"]["allow"]
    assert data["effortLevel"] == "medium"


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    settings.upsert_claude_settings(tmp_path)
    first = json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))
    settings.upsert_claude_settings(tmp_path)
    second = json.loads(_settings_path(tmp_path).read_text(encoding="utf-8"))
    assert first == second


def test_remove_returns_false_when_no_file(tmp_path: Path) -> None:
    assert settings.remove_claude_settings(tmp_path) is False


def test_remove_returns_false_when_no_sciona_entries(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    target.write_text(json.dumps({"permissions": {"allow": ["Bash(git status)"]}}), encoding="utf-8")
    assert settings.remove_claude_settings(tmp_path) is False


def test_remove_strips_sciona_entries_preserves_others(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    settings.upsert_claude_settings(tmp_path)
    target = _settings_path(tmp_path)
    data = json.loads(target.read_text(encoding="utf-8"))
    data["permissions"]["allow"].insert(0, "Bash(git status)")
    target.write_text(json.dumps(data), encoding="utf-8")

    removed = settings.remove_claude_settings(tmp_path)
    assert removed is True
    result = json.loads(target.read_text(encoding="utf-8"))
    allow = result["permissions"]["allow"]
    assert "Bash(git status)" in allow
    assert not any(e.startswith(settings.SCIONA_MARKER) for e in allow)


def test_remove_deletes_file_when_only_sciona_content(tmp_path: Path) -> None:
    settings.upsert_claude_settings(tmp_path)
    target = _settings_path(tmp_path)
    assert target.exists()
    removed = settings.remove_claude_settings(tmp_path)
    assert removed is True
    assert not target.exists()


def test_remove_preserves_other_top_level_keys(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    target.write_text(json.dumps({"effortLevel": "high"}), encoding="utf-8")
    settings.upsert_claude_settings(tmp_path)
    settings.remove_claude_settings(tmp_path)
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data.get("effortLevel") == "high"
    assert "permissions" not in data


def test_upsert_raises_on_malformed_json(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    target.write_text("not valid json {{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        settings.upsert_claude_settings(tmp_path)
    assert target.read_text(encoding="utf-8") == "not valid json {{"


def test_upsert_raises_on_non_object_json(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    target.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="does not contain a JSON object"):
        settings.upsert_claude_settings(tmp_path)
    assert target.read_text(encoding="utf-8") == "[1, 2, 3]"


def test_remove_raises_on_malformed_json(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    target.write_text("not valid json {{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        settings.remove_claude_settings(tmp_path)
    assert target.read_text(encoding="utf-8") == "not valid json {{"


def test_upsert_raises_on_symlink(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    other = tmp_path / "other.json"
    other.write_text("{}", encoding="utf-8")
    target.symlink_to(other)
    with pytest.raises(ValueError, match="symbolic link"):
        settings.upsert_claude_settings(tmp_path)
    assert other.read_text(encoding="utf-8") == "{}"


def test_remove_raises_on_symlink(tmp_path: Path) -> None:
    (tmp_path / settings.CLAUDE_DIR).mkdir()
    target = _settings_path(tmp_path)
    payload = {"permissions": {"allow": [f"{settings.SCIONA_MARKER} Bash(sciona build)"]}}
    other = tmp_path / "other.json"
    other.write_text(json.dumps(payload), encoding="utf-8")
    target.symlink_to(other)
    with pytest.raises(ValueError, match="symbolic link"):
        settings.remove_claude_settings(tmp_path)
