"""Managed AGENTS.md generation helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import inspect

from ..reducers.registry import get_reducers

BEGIN_MARKER = "<!-- sciona:begin -->"
END_MARKER = "<!-- sciona:end -->"
AGENTS_FILENAME = "AGENTS.md"
TEMPLATE_FILENAME = "agents_template.md"


def build_agents_block() -> str:
    reducers = get_reducers()
    reducers = _filter_hidden_reducers(reducers)
    template = _load_template()
    content = template.format(
        COMMON_TASKS=_render_common_tasks(reducers),
    )
    return "\n".join([BEGIN_MARKER, content.strip(), END_MARKER]).rstrip() + "\n"


def upsert_agents_file(repo_root: Path, *, mode: str = "append") -> Path:
    target = Path(repo_root) / AGENTS_FILENAME
    block = build_agents_block()
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


def _filter_hidden_reducers(reducers):
    hidden = {"source_snippet"}
    return {key: value for key, value in reducers.items() if key not in hidden}


def _load_template() -> str:
    path = Path(__file__).parent / "templates" / TEMPLATE_FILENAME
    return path.read_text(encoding="utf-8")


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
        if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
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
    ("Orientation", ["codebase_orientation", "structural_index"]),
    ("Structure (module/class/callable)", ["module_summary", "class_summary", "callable_summary"]),
    ("Dependencies / imports", ["dependency_summary", "dependency_edges", "importers_index"]),
    ("Calls / call graph", ["call_graph", "callsite_index"]),
    ("References / usages", ["symbol_references"]),
    ("File navigation (codebase-scoped; filters supported)", ["module_file_map", "file_outline"]),
    ("Context bundle", ["callable_context_bundle"]),
    ("Code text (last resort)", ["callable_source", "concatenated_source"]),
    ("Public surface", ["public_surface_index"]),
]


__all__ = [
    "AGENTS_FILENAME",
    "BEGIN_MARKER",
    "END_MARKER",
    "build_agents_block",
    "remove_agents_block",
    "upsert_agents_file",
]
