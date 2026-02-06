# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Managed AGENTS.md generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import inspect

from .config import io as config_io
from .config import defaults as config_defaults
from .errors import ConfigError


BEGIN_MARKER = "<!-- sciona:begin -->"
END_MARKER = "<!-- sciona:end -->"
AGENTS_FILENAME = "AGENTS.md"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "agents_template.md"

_LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
}


def build_agents_block(repo_root: Path, reducers) -> str:
    template = _load_template()
    content = template.format(
        COMMON_TASKS=_render_common_tasks(reducers),
        TRACKED_FILE_SCOPE=_render_tracked_file_scope(repo_root),
    )
    return "\n".join([BEGIN_MARKER, content.strip(), END_MARKER]).rstrip() + "\n"


def upsert_agents_file(repo_root: Path, *, mode: str = "append", reducers) -> Path:
    target = Path(repo_root) / AGENTS_FILENAME
    block = build_agents_block(repo_root, reducers)
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
        extensions.extend(_LANGUAGE_EXTENSIONS.get(name, []))
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
    lines: list[str] = []
    for title, reducer_ids in _COMMON_TASK_SECTIONS:
        commands = _commands_for_reducers(reducer_ids, reducers)
        if not commands:
            continue
        lines.append(f"{title}:")
        for command in commands:
            lines.append(f"- {command}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _commands_for_reducers(reducer_ids: Iterable[str], reducers) -> list[str]:
    commands: list[str] = []
    for reducer_id in reducer_ids:
        entry = reducers.get(reducer_id)
        if entry is None:
            continue
        commands.append(_format_reducer_command(reducer_id, entry.module))
    return commands


def _format_reducer_command(reducer_id: str, reducer_module) -> str:
    render = getattr(reducer_module, "render", None)
    if render is None:
        return f"sciona reducer --id {reducer_id}"
    signature = inspect.signature(render)
    args = []
    for name, param in signature.parameters.items():
        if name in {"snapshot_id", "conn", "repo_root"}:
            continue
        if param.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue
        flag = f"--{name.replace('_', '-')}"
        if name == "extras":
            args.append(f"[{flag}]")
            continue
        placeholder = f"<{name}>"
        if param.default is inspect._empty:
            args.append(f"{flag} {placeholder}")
        else:
            args.append(f"[{flag} {placeholder}]")
    rendered_args = " ".join(args)
    if rendered_args:
        return f"sciona reducer --id {reducer_id} {rendered_args}"
    return f"sciona reducer --id {reducer_id}"


_COMMON_TASK_SECTIONS = [
    ("Orientation", ["structural_index"]),
    (
        "Structure (module/class/callable)",
        ["module_overview", "class_overview", "callable_overview"],
    ),
    ("Dependencies / imports", ["dependency_edges", "importers_index"]),
    ("Calls / call graph", ["call_graph", "callsite_index"]),
    ("References / usages", ["symbol_references"]),
    (
        "File navigation (codebase-scoped; filters supported)",
        ["module_file_map", "file_outline"],
    ),
    ("Code text (last resort)", ["callable_source", "concatenated_source"]),
]


__all__ = [
    "AGENTS_FILENAME",
    "BEGIN_MARKER",
    "END_MARKER",
    "build_agents_block",
    "remove_agents_block",
    "upsert_agents_file",
]
