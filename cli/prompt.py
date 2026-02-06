"""CLI helper to compile prompts."""

from __future__ import annotations

from typing import Optional

import json

import typer

from ..api import prompts as prompt_api
from . import render as cli_render
from .utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
    normalize_flag_args,
    parse_extra_args,
)


def register(app: typer.Typer) -> None:
    prompt_app = typer.Typer(help="Prompt registry helpers.", no_args_is_help=True)

    @prompt_app.command(
        "run",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def run_prompt(
        ctx: typer.Context,
        prompt_id: str = typer.Argument(..., help="Prompt id (from registry)."),
        answer: bool = typer.Option(
            False,
            "--answer",
            help="Send the prompt to the configured LLM and print the answer.",
        ),
        json_output: bool = typer.Option(
            False, "--json", help="Emit machine-readable JSON output."
        ),
        node_id: Optional[str] = typer.Option(
            None, "--id", help="Use a structural id directly."
        ),
        callable_id: Optional[str] = typer.Option(
            None, "--callable-id", help="Callable id (function or method)."
        ),
        function_id: Optional[str] = typer.Option(
            None, "--function-id", help="Function id."
        ),
        method_id: Optional[str] = typer.Option(None, "--method-id", help="Method id."),
        class_id: Optional[str] = typer.Option(None, "--class-id", help="Class id."),
        module_id: Optional[str] = typer.Option(None, "--module-id", help="Module id."),
    ) -> None:
        """Compile and print a prompt or LLM answer (latest committed snapshot only)."""
        repo_root = prompt_api.ensure_prompt_preconditions()
        extra_args = list(ctx.args)
        explicit_ids = {
            "callable_id": callable_id,
            "function_id": function_id,
            "method_id": method_id,
            "class_id": class_id,
            "module_id": module_id,
        }
        if node_id and detail:
            raise typer.BadParameter("Cannot use both a qualified name and --id.")
        if node_id and any(value for value in explicit_ids.values()):
            raise typer.BadParameter("Cannot use --id with a specific id option.")
        provided_ids = [name for name, value in explicit_ids.items() if value]
        if len(provided_ids) > 1:
            raise typer.BadParameter("Provide only one specific id option.")
        arg_map = parse_extra_args(normalize_flag_args(extra_args))
        for name, value in explicit_ids.items():
            if not value:
                continue
            if name in arg_map:
                raise typer.BadParameter(f"Duplicate value for '{name}'.")
            arg_map[name] = value
        prompt_name = _require_prompt_id(prompt_id, repo_root=repo_root)
        if answer:
            if not prompt_api.prompt_allows_answer(prompt_name):
                raise typer.BadParameter("This prompt does not support --answer.")
            prompt_text, snapshot_id, resolved_arg_map = cli_call(
                prompt_api.compile_prompt_payload,
                prompt_name,
                arg_map=arg_map,
                node_id=node_id,
            )
            answer_text = cli_call(
                prompt_api.answer_prompt_text_by_name,
                prompt_name,
                arg_map=arg_map,
                node_id=node_id,
            )
            if json_output:
                sections = prompt_api.extract_prompt_sections(prompt_text)
                warning = get_dirty_worktree_warning()
                payload: dict[str, object] = {
                    "prompt_name": prompt_name,
                    "snapshot_id": snapshot_id,
                    "node_id": node_id,
                    "arg_map": arg_map,
                    "resolved_arg_map": resolved_arg_map,
                    "prompt": prompt_text,
                    "prompt_header": sections.get("prompt_header"),
                    "prompt_body": sections.get("prompt_body"),
                    "instructions": sections.get("instructions"),
                    "evidence": sections.get("evidence"),
                    "answer": answer_text,
                }
                if warning:
                    payload["warning"] = warning
                typer.echo(json.dumps(payload))
            else:
                emit_dirty_worktree_warning()
                typer.echo(answer_text)
        else:
            prompt_text, snapshot_id, resolved_arg_map = cli_call(
                prompt_api.compile_prompt_payload,
                prompt_name,
                arg_map=arg_map,
                node_id=node_id,
            )
            if json_output:
                sections = prompt_api.extract_prompt_sections(prompt_text)
                warning = get_dirty_worktree_warning()
                payload: dict[str, object] = {
                    "prompt_name": prompt_name,
                    "snapshot_id": snapshot_id,
                    "node_id": node_id,
                    "arg_map": arg_map,
                    "resolved_arg_map": resolved_arg_map,
                    "prompt": prompt_text,
                    "prompt_header": sections.get("prompt_header"),
                    "prompt_body": sections.get("prompt_body"),
                    "instructions": sections.get("instructions"),
                    "evidence": sections.get("evidence"),
                }
                if warning:
                    payload["warning"] = warning
                typer.echo(json.dumps(payload))
            else:
                emit_dirty_worktree_warning()
                typer.echo(prompt_text)

    @prompt_app.command("list")
    def list_prompts() -> None:
        """List prompts with CLI call signatures (warns if dirty)."""
        repo_root = prompt_api.ensure_prompt_preconditions()
        emit_dirty_worktree_warning()
        entries = _prompt_entries(repo_root=repo_root)
        lines = ["Prompts:"]
        for entry in entries:
            call = _format_prompt_call(entry)
            lines.append(f"  {call}")
        cli_render.emit(lines)

    @prompt_app.command("info")
    def prompt_info(
        prompt_id: Optional[str] = typer.Option(
            None,
            "--id",
            help="Filter to a single prompt id (e.g., preflight_v1).",
        ),
    ) -> None:
        """Show prompt metadata (warns if dirty)."""
        repo_root = prompt_api.ensure_prompt_preconditions()
        emit_dirty_worktree_warning()
        entries = _prompt_entries(repo_root=repo_root)
        if prompt_id:
            entries = [entry for entry in entries if entry["prompt_id"] == prompt_id]
            if not entries:
                raise typer.BadParameter(f"Unknown prompt '{prompt_id}'.")
        lines: list[str] = []
        for index, entry in enumerate(entries):
            if index:
                lines.append("")
            lines.extend(_render_prompt_info(entry))
        cli_render.emit(lines)

    app.add_typer(prompt_app, name="prompt")


_STANDARD_PROMPT_ARGS = {
    "callable_id": "--callable-id CALLABLE_ID",
    "function_id": "--function-id FUNCTION_ID",
    "method_id": "--method-id METHOD_ID",
    "class_id": "--class-id CLASS_ID",
    "module_id": "--module-id MODULE_ID",
}


def _prompt_entries(*, repo_root: Optional[Path]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for name, entry in prompt_api.get_prompts(repo_root).items():
        if entry.get("_source") == "addon":
            continue
        if entry.get("kind") in {"internal", "addon"}:
            continue
        normalized = dict(entry)
        normalized["prompt_id"] = name
        entries.append(normalized)
    entries.sort(key=lambda item: item["prompt_id"])
    return entries


def _prompt_summary(entry: dict[str, object]) -> str:
    summary = entry.get("summary") or entry.get("description")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return "Prompt."


def _format_prompt_call(entry: dict[str, object]) -> str:
    required_flags, optional_flags = _collect_prompt_options(entry)
    base_flags = ["[--answer]", "[--json]", "[--id NODE_ID]"]
    options = base_flags + required_flags + optional_flags
    rendered = " ".join(options)
    return f"prompt run {entry['prompt_id']} {rendered}".rstrip()


def _collect_prompt_options(entry: dict[str, object]) -> tuple[list[str], list[str]]:
    required_flags: list[str] = []
    optional_flags: list[str] = []
    seen_required: set[str] = set()
    seen_optional: set[str] = set()
    required_args = [
        arg for arg in entry.get("required_args") or [] if isinstance(arg, str)
    ]
    optional_args = [
        arg for arg in entry.get("optional_args") or [] if isinstance(arg, str)
    ]
    default_args = [
        arg for arg in entry.get("default_args") or {} if isinstance(arg, str)
    ]
    for arg in required_args:
        flag = _STANDARD_PROMPT_ARGS.get(
            arg, f"--{arg.replace('_', '-')} {arg.upper()}"
        )
        if flag in seen_required:
            continue
        seen_required.add(flag)
        required_flags.append(flag)
    for arg in optional_args:
        flag = _STANDARD_PROMPT_ARGS.get(
            arg, f"--{arg.replace('_', '-')} {arg.upper()}"
        )
        if flag in seen_required or flag in seen_optional:
            continue
        seen_optional.add(flag)
        optional_flags.append(f"[{flag}]")
    for arg in default_args:
        flag = _STANDARD_PROMPT_ARGS.get(
            arg, f"--{arg.replace('_', '-')} {arg.upper()}"
        )
        if flag in seen_required or flag in seen_optional:
            continue
        seen_optional.add(flag)
        optional_flags.append(f"[{flag}]")
    return required_flags, optional_flags


def _require_prompt_id(prompt_id: str, *, repo_root: Optional[Path]) -> str:
    if not prompt_id:
        raise typer.BadParameter("Missing prompt id.")
    prompt_id = prompt_id.strip()
    entry = prompt_api.get_prompts(repo_root).get(prompt_id)
    if not entry or entry.get("_source") == "addon" or entry.get("kind") == "internal":
        raise typer.BadParameter(f"Unknown prompt '{prompt_id}'.")
    return prompt_id


def _render_prompt_info(entry: dict[str, object]) -> list[str]:
    lines = [
        f"Prompt: {entry['prompt_id']}",
        f"Kind: {entry.get('kind')}",
    ]
    summary = _prompt_summary(entry)
    if summary:
        lines.append("")
        lines.append("Summary:")
        lines.append(f"  {summary}")
    reducers = entry.get("reducers") or []
    if reducers:
        lines.append("")
        lines.append("Reducers:")
        for reducer in reducers:
            lines.append(f"  - {reducer}")
    required = entry.get("required_args") or []
    optional = entry.get("optional_args") or []
    if required or optional:
        lines.append("")
        lines.append("Arguments:")
        if required:
            lines.append("  required:")
            for arg in required:
                lines.append(f"    - {arg}")
        if optional:
            lines.append("  optional:")
            for arg in optional:
                lines.append(f"    - {arg}")
    if "spec" in entry:
        lines.append("")
        lines.append(f"Spec: {entry.get('spec')}")
    if "spec_root" in entry and entry.get("spec_root"):
        lines.append(f"Spec root: {entry.get('spec_root')}")
    if "wording" in entry:
        lines.append("Wording: inline")
    allow_answer = entry.get("allow_answer")
    if allow_answer is not None:
        lines.append(f"Allow answer: {'yes' if allow_answer else 'no'}")
    return lines
