"""CLI helpers for error handling and argument parsing."""

from __future__ import annotations

import json
import re
import traceback

import typer

from ..api import repo as api_repo
from ..api import runtime as api_runtime
from . import render as cli_render
from .errors import handle_cli_error


def cli_call(func, *args, **kwargs):
    """Invoke CLI helpers and translate errors into CLI exits."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        try:
            handle_cli_error(exc)
        except typer.Exit:
            raise
        except Exception:
            typer.secho(f"Internal error: {exc}", fg=typer.colors.RED)
            if api_runtime.debug_enabled():
                typer.secho(traceback.format_exc(), fg=typer.colors.YELLOW, err=True)
            raise typer.Exit(code=1) from exc
        raise


runtime_call = cli_call
setup_call = cli_call


def parse_extra_args(args: list[str]) -> dict[str, str]:
    """Parse --key value or --key=value args into a string-only key/value map; no positional args or coercion. This function is part of the CLI ABI; do not change without a version bump."""
    parsed: dict[str, str] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if token.startswith("--") and "=" in token:
            key, value = token[2:].split("=", 1)
            normalized = key.replace("-", "_")
            _validate_extra_arg(normalized, value)
            parsed[normalized] = value
            index += 1
            continue
        if token.startswith("--"):
            key = token[2:].replace("-", "_")
            if index + 1 >= len(args):
                raise typer.BadParameter(f"Missing value for '{token}'.")
            value = args[index + 1]
            _validate_extra_arg(key, value)
            parsed[key] = value
            index += 2
            continue
        raise typer.BadParameter(f"Unexpected argument '{token}'.")
    return parsed


def normalize_flag_args(args: list[str]) -> list[str]:
    """Allow bare boolean flags like --extras by coercing them to true."""
    normalized: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--extras":
            next_token = args[index + 1] if index + 1 < len(args) else None
            if next_token is None or next_token.startswith("--"):
                normalized.extend([token, "true"])
                index += 1
                continue
        normalized.append(token)
        index += 1
    return normalized


def parse_payload(text: str) -> dict | None:
    try:
        return json.loads(strip_json_fence(text))
    except Exception:
        return None


def strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed


def emit_dirty_worktree_warning(repo_root=None) -> None:
    warning = get_dirty_worktree_warning(repo_root)
    if warning:
        cli_render.emit_warning([warning])


def get_dirty_worktree_warning(repo_root=None) -> str | None:
    try:
        return api_repo.dirty_worktree_warning(repo_root)
    except Exception:
        return None


def _validate_extra_arg(key: str, value: str) -> None:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key or ""):
        raise typer.BadParameter(f"Invalid parameter name '{key}'.")
    if key.startswith("__"):
        raise typer.BadParameter(f"Invalid parameter name '{key}'.")
    if any(ch in value for ch in ("\x00", "\n", "\r")):
        raise typer.BadParameter(f"Invalid value for '{key}'.")
    if any(ch in value for ch in (";", "|", "&", "`")):
        raise typer.BadParameter(f"Invalid value for '{key}'.")
