from pathlib import Path

import pytest

from sciona.prompts import get_prompts

from .helpers import seed_repo_with_snapshot


def _write_prompt(repo_root: Path, registry_text: str, spec_name: str, spec_text: str) -> None:
    prompts_dir = repo_root / ".sciona" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "registry.yaml").write_text(registry_text, encoding="utf-8")
    (prompts_dir / spec_name).write_text(spec_text, encoding="utf-8")


def test_prompt_rejects_duplicate_placeholders(tmp_path):
    repo_root, _snapshot_id = seed_repo_with_snapshot(tmp_path)
    registry_text = """bad_duplicate_v1:
  spec: bad_duplicate_v1.md
  reducers:
    - fan_summary
  required_args:
    - function_id
"""
    spec_text = """Duplicate placeholder test.
{FAN_SUMMARY}
{FAN_SUMMARY}
"""
    _write_prompt(repo_root, registry_text, "bad_duplicate_v1.md", spec_text)

    with pytest.raises(ValueError, match=r"Duplicate placeholders"):
        get_prompts(repo_root)


def test_prompt_requires_bijection(tmp_path):
    repo_root, _snapshot_id = seed_repo_with_snapshot(tmp_path)
    registry_text = """bad_missing_v1:
  spec: bad_missing_v1.md
  reducers:
    - hotspot_summary
  required_args:
    - limit
"""
    spec_text = """Missing placeholder test.
{STRUCTURAL_INDEX}
"""
    _write_prompt(repo_root, registry_text, "bad_missing_v1.md", spec_text)

    with pytest.raises(ValueError, match=r"Missing placeholders"):
        get_prompts(repo_root)


def test_prompt_warns_unused_args(tmp_path, caplog):
    repo_root, _snapshot_id = seed_repo_with_snapshot(tmp_path)
    registry_text = """unused_args_v1:
  spec: unused_args_v1.md
  reducers:
    - fan_summary
  required_args:
    - unused_required_arg
  optional_args:
    - unused_optional_arg
"""
    spec_text = """Unused args test.
{FAN_SUMMARY}
"""
    _write_prompt(repo_root, registry_text, "unused_args_v1.md", spec_text)

    with caplog.at_level("WARNING"):
        get_prompts(repo_root)

    assert "unused by reducers" in caplog.text
    assert "unused_optional_arg" in caplog.text
