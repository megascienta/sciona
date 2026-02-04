"""Configuration IO utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from ...runtime import config_defaults as defaults
from ...runtime.paths import get_config_path
from .errors import RuntimeConfigError


def load_raw_config(repo_root: Path) -> Dict[str, Any]:
    config_path = get_config_path(repo_root)
    if not config_path.exists():
        raise RuntimeConfigError(
            "Missing .sciona/config.yaml. Run 'sciona init' and edit the generated template before building.",
            code="missing_config",
            hint="Run `sciona init` and edit .sciona/config.yaml to enable languages.",
            exit_code=1,
        )
    try:
        raw_text = config_path.read_text(encoding="utf-8")
        if len(raw_text.encode("utf-8")) > 1_000_000:
            raise RuntimeConfigError(
                "Config file too large.",
                code="invalid_config",
                hint="Reduce .sciona/config.yaml size.",
                exit_code=1,
            )
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise RuntimeConfigError(
            "Failed to parse .sciona/config.yaml",
            code="invalid_config",
            hint="Fix the YAML syntax in .sciona/config.yaml.",
            exit_code=1,
        ) from exc
    if not isinstance(data, dict):
        return {}
    return data


def write_default_config(repo_root: Path) -> None:
    """Create .sciona/config.yaml with language defaults if missing."""
    config_path = get_config_path(repo_root)
    if config_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["languages:"]
    for name, lang_defaults in defaults.LANGUAGE_DEFAULTS.items():
        enabled = "true" if lang_defaults["enabled"] else "false"
        lines.append(f"  {name}:")
        lines.append(f"    enabled: {enabled}")
    lines.extend(
        [
            "",
            "discovery:",
            "  exclude_globs: []",
            "",
            "database:",
            f"  timeout: {defaults.DEFAULT_DB_TIMEOUT}",
            "",
            "git:",
            f"  timeout: {defaults.DEFAULT_GIT_TIMEOUT}",
            "",
            "logging:",
            f'  level: "{defaults.DEFAULT_LOG_LEVEL}"',
            f"  debug: {str(defaults.DEFAULT_LOG_DEBUG).lower()}",
            f"  structured: {str(defaults.DEFAULT_LOG_STRUCTURED).lower()}",
            "  module_levels: {}",
            "",
            "llm:",
            f'  provider: "{defaults.DEFAULT_LLM_PROVIDER}"',
            f'  model: "{defaults.DEFAULT_LLM_MODEL}"',
            "  api_endpoint: null",
            "  api_key: null",
            f"  temperature: {defaults.DEFAULT_TEMPERATURE}",
            f"  timeout: {defaults.DEFAULT_LLM_TIMEOUT}",
            f"  max_retries: {defaults.DEFAULT_LLM_MAX_RETRIES}",
            "",
        ]
    )
    template = "\n".join(lines) + "\n"
    config_path.write_text(template, encoding="utf-8")


def load_config_text(repo_root: Path) -> str | None:
    """Return the current config contents if present."""
    config_path = get_config_path(repo_root)
    if config_path.exists():
        return config_path.read_text(encoding="utf-8")
    return None


def write_config_text(repo_root: Path, contents: str) -> None:
    """Write the provided config contents, creating parent directories as needed."""
    config_path = get_config_path(repo_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(contents, encoding="utf-8")


__all__ = [
    "load_config_text",
    "load_raw_config",
    "write_config_text",
    "write_default_config",
]
