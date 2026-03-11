# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Managed AGENTS.md generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ...code_analysis.core.extract.registry import extensions_for_language
from ..config import io as config_io
from ..config import defaults as config_defaults
from ..errors import ConfigError
from sciona.runtime.reducers.metadata import CATEGORY_ORDER
from sciona.runtime.reducers.listing import render_reducer_list


BEGIN_MARKER = "<!-- sciona:begin -->"
END_MARKER = "<!-- sciona:end -->"
AGENTS_FILENAME = "AGENTS.md"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "agents_template.md"

def build_agents_block(
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
        CMD_VERSION=commands.get("version", "sciona --version"),
        CMD_INIT=commands.get("init", "sciona init"),
        CMD_AGENTS=commands.get("agents", "sciona agents"),
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


def upsert_agents_file(
    repo_root: Path,
    *,
    mode: str = "append",
    reducers,
    commands: Mapping[str, str] | None = None,
) -> Path:
    target = Path(repo_root) / AGENTS_FILENAME
    block = build_agents_block(repo_root, reducers, commands=commands)
    if mode not in {"append", "overwrite"}:
        raise ValueError("mode must be 'append' or 'overwrite'.")
    if mode == "overwrite" or not target.exists():
        target.write_text(block, encoding="utf-8")
        return target
    text = target.read_text(encoding="utf-8")
    updated = _replace_or_append_block(text, block)
    target.write_text(updated, encoding="utf-8")
    return target


def remove_agents_block(repo_root: Path) -> bool:
    target = Path(repo_root) / AGENTS_FILENAME
    if not target.exists():
        return False
    text = target.read_text(encoding="utf-8")
    if BEGIN_MARKER not in text or END_MARKER not in text:
        return False
    cleaned = _remove_block(text)
    if not cleaned.strip():
        target.unlink()
        return True
    target.write_text(cleaned, encoding="utf-8")
    return True


def _replace_or_append_block(text: str, block: str) -> str:
    if BEGIN_MARKER in text and END_MARKER in text:
        return _replace_block(text, block)
    suffix = "" if text.endswith("\n") else "\n"
    return f"{text}{suffix}\n{block}"


def _replace_block(text: str, block: str) -> str:
    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER) + len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    parts = []
    if before:
        parts.append(before)
    parts.append(block.rstrip())
    if after:
        parts.append(after)
    return "\n\n".join(parts).rstrip() + "\n"


def _remove_block(text: str) -> str:
    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER) + len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    if before and after:
        return f"{before}\n\n{after}".rstrip() + "\n"
    if before:
        return before.rstrip() + "\n"
    if after:
        return after.rstrip() + "\n"
    return ""


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

    extensions = []
    for name in enabled:
        extensions.extend(extensions_for_language(name))
    extensions = sorted(set(extensions))

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
    entries = []
    for reducer_id, entry in reducers.items():
        entries.append(
            {
                "reducer_id": reducer_id,
                "category": entry.category,
                "summary": entry.summary,
            }
        )
    return "\n".join(render_reducer_list(entries, reducers, include_prefix=True))

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
    "agents": "sciona agents",
    "reducer_list": "sciona reducer list",
    "reducer_info": "sciona reducer info --id <reducer_id>",
    "reducer": "sciona reducer --id <reducer_id>",
    "build": "sciona build",
    "search": "sciona search <query> --kind module|type|class|function|method|callable --limit 10 --json",
    "resolve": "sciona resolve <identifier> --kind module|type|class|function|method|callable --json",
}


__all__ = [
    "AGENTS_FILENAME",
    "BEGIN_MARKER",
    "END_MARKER",
    "build_agents_block",
    "remove_agents_block",
    "upsert_agents_file",
]
