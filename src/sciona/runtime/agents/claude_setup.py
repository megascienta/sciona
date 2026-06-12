# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Managed CLAUDE.md generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..config import io as config_io
from ..config import defaults as config_defaults
from ..config.language_scope import tracked_extensions_for_enabled_names
from ..errors import ConfigError
from sciona.runtime.reducers.metadata import CATEGORY_ORDER
from sciona.runtime.reducers.listing import (
    render_reducer_list,
    render_reducer_usage_notes,
)
from ._block_utils import (
    BEGIN_MARKER,
    END_MARKER,
    check_not_symlink as _check_not_symlink,
    replace_or_append_block as _replace_or_append_block,
    remove_block as _remove_block,
)

CLAUDE_FILENAME = "CLAUDE.md"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "claude_template.md"


def build_claude_block(
    repo_root: Path,
    reducers,
    *,
    commands: Mapping[str, str] | None = None,
) -> str:
    template = _load_template()
    commands = _merge_commands(commands)
    content = template.format(
        COMMON_TASKS=_render_common_tasks(reducers),
        INVESTIGATION_ROLE_CATEGORIES=_render_investigation_role_categories(reducers),
        SOURCE_REDUCER_LIST=_render_source_reducer_list(reducers),
        ANOMALY_DETECTOR_LIST=_render_anomaly_detector_list(reducers),
        REDUCER_USAGE_NOTES=_render_reducer_usage_notes(reducers),
        CMD_VERSION=commands.get("version", "sciona --version"),
        CMD_INIT=commands.get("init", "sciona init"),
        CMD_CLAUDE=commands.get("claude", "sciona claude"),
        CMD_REDUCER_LIST=commands.get("reducer_list", "sciona reducer list"),
        CMD_REDUCER_INFO=commands.get(
            "reducer_info", "sciona reducer info --id <reducer_id>"
        ),
        CMD_REDUCER=commands.get("reducer", "sciona reducer --id <reducer_id>"),
        CMD_BUILD=commands.get("build", "sciona build"),
        CMD_SEARCH=commands.get(
            "search",
            "sciona search <query> --kind module|type|class|function|method|callable --limit 10 --json",
        ),
        CMD_RESOLVE=commands.get(
            "resolve",
            "sciona resolve <identifier> --kind module|type|class|function|method|callable --json",
        ),
        SCIONA_CONFIG_PATH=".sciona/config.yaml",
        TRACKED_FILE_SCOPE=_render_tracked_file_scope(repo_root),
    )
    return "\n".join([BEGIN_MARKER, content.strip(), END_MARKER]).rstrip() + "\n"


def upsert_claude_file(
    repo_root: Path,
    *,
    mode: str = "append",
    reducers,
    commands: Mapping[str, str] | None = None,
) -> Path:
    target = Path(repo_root) / CLAUDE_FILENAME
    _check_not_symlink(target)
    block = build_claude_block(repo_root, reducers, commands=commands)
    if mode not in {"append", "overwrite"}:
        raise ValueError("mode must be 'append' or 'overwrite'.")
    if mode == "overwrite" or not target.exists():
        target.write_text(block, encoding="utf-8")
        return target
    text = target.read_text(encoding="utf-8")
    updated = _replace_or_append_block(text, block)
    target.write_text(updated, encoding="utf-8")
    return target


def remove_claude_block(repo_root: Path) -> bool:
    target = Path(repo_root) / CLAUDE_FILENAME
    if not target.exists():
        return False
    _check_not_symlink(target)
    text = target.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return False
    cleaned = _remove_block(text)
    if not cleaned.strip():
        target.unlink()
        return True
    target.write_text(cleaned, encoding="utf-8")
    return True


def _load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def _render_tracked_file_scope(repo_root: Path) -> str:
    try:
        raw = config_io.load_raw_config(repo_root)
    except ConfigError:
        return "\n".join(
            [
                "- Enabled languages: unknown (missing .sciona/config.yaml)",
                "- Tracked file types: unknown",
                "- Discovery excludes: unknown",
            ]
        )

    lang_block = raw.get("languages", {}) if isinstance(raw, dict) else {}
    enabled = []
    for name, defaults in config_defaults.LANGUAGE_DEFAULTS.items():
        user_cfg = lang_block.get(name, {}) if isinstance(lang_block, dict) else {}
        if bool(user_cfg.get("enabled", defaults["enabled"])):
            enabled.append(name)
    enabled = sorted(enabled)

    extensions = sorted(tracked_extensions_for_enabled_names(enabled))

    discovery_block = raw.get("discovery", {}) if isinstance(raw, dict) else {}
    exclude_globs = discovery_block.get("exclude_globs", [])
    if not isinstance(exclude_globs, list):
        exclude_globs = []
    cleaned = [str(entry) for entry in exclude_globs if entry]

    enabled_text = ", ".join(enabled) if enabled else "none"
    extensions_text = ", ".join(extensions) if extensions else "none"
    excludes_text = ", ".join(cleaned) if cleaned else "none"
    return "\n".join(
        [
            f"- Enabled languages: {enabled_text}",
            f"- Tracked file types: {extensions_text}",
            f"- Discovery excludes: {excludes_text}",
        ]
    )


def _render_common_tasks(reducers) -> str:
    entries = _reducer_metadata_entries(reducers)
    return "\n".join(render_reducer_list(entries, reducers, include_prefix=True))


def _render_reducer_usage_notes(reducers) -> str:
    entries = _reducer_metadata_entries(reducers)
    return "\n".join(render_reducer_usage_notes(entries, reducers, include_prefix=True))


def _reducer_metadata_entries(reducers) -> list[dict[str, object]]:
    entries = []
    for reducer_id, entry in reducers.items():
        entries.append(
            {
                "reducer_id": reducer_id,
                "category": entry.category,
                "summary": entry.summary,
                "args": [
                    {
                        "name": arg.name,
                        "type": arg.type,
                        "description": arg.description,
                        "required": arg.required,
                        "enum": list(arg.enum),
                        "default": arg.default,
                    }
                    for arg in entry.args
                ],
                "requires": entry.requires,
            }
        )
    return entries


def _render_investigation_role_categories(reducers) -> str:
    lines: list[str] = []
    for role_name in CATEGORY_ORDER:
        label = f"{role_name.capitalize()} reducers"
        reducer_ids = _sorted_reducer_ids_by_categories(reducers, {role_name})
        rendered = ", ".join(reducer_ids) if reducer_ids else "(none)"
        lines.append(f"**{label}:**")
        lines.append(rendered)
        lines.append("")
    return "\n".join(lines).rstrip()


def _render_source_reducer_list(reducers) -> str:
    reducer_ids = _sorted_reducer_ids_by_categories(reducers, {"source"})
    return "\n".join(f"- `{reducer_id}`" for reducer_id in reducer_ids)


def _render_anomaly_detector_list(reducers) -> str:
    reducer_ids = sorted(
        str(reducer_id)
        for reducer_id, entry in reducers.items()
        if bool(getattr(entry, "anomaly_detector", False))
    )
    return "\n".join(f"- `{reducer_id}`" for reducer_id in reducer_ids)


def _sorted_reducer_ids_by_categories(
    reducers,
    categories: set[str],
) -> list[str]:
    return _sorted_reducer_ids(reducers, categories=categories)


def _sorted_reducer_ids(
    reducers,
    *,
    categories: set[str] | None = None,
    reducer_ids: set[str] | None = None,
) -> list[str]:
    selected: list[str] = []
    for reducer_id, entry in reducers.items():
        category = str(getattr(entry, "category", "") or "")
        if categories is not None and category not in categories:
            continue
        if reducer_ids is not None and str(reducer_id) not in reducer_ids:
            continue
        selected.append(str(reducer_id))
    return sorted(selected)


def _merge_commands(commands: Mapping[str, str] | None) -> dict[str, str]:
    merged = dict(_DEFAULT_COMMANDS)
    if commands:
        merged.update(commands)
    return merged


_DEFAULT_COMMANDS = {
    "version": "sciona --version",
    "init": "sciona init",
    "claude": "sciona claude",
    "reducer_list": "sciona reducer list",
    "reducer_info": "sciona reducer info --id <reducer_id>",
    "reducer": "sciona reducer --id <reducer_id>",
    "build": "sciona build",
    "search": "sciona search <query> --kind module|type|class|function|method|callable --limit 10 --json",
    "resolve": "sciona resolve <identifier> --kind module|type|class|function|method|callable --json",
}


__all__ = [
    "CLAUDE_FILENAME",
    "BEGIN_MARKER",
    "END_MARKER",
    "build_claude_block",
    "remove_claude_block",
    "upsert_claude_file",
]
