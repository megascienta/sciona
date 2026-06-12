# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer commands."""

from __future__ import annotations

import types
from typing import Optional, Union, get_args, get_origin

import json

import typer
from typer.core import TyperGroup

from .. import reducer_ops
from ...api import errors as api_errors
from ...runtime import paths as runtime_paths
from ...runtime.reducers.listing import render_reducer_list
from ..support.utils import (
    cli_call,
    emit_dirty_worktree_warning,
    emit_user_warning,
    get_dirty_worktree_warning,
    normalize_flag_args,
    parse_extra_args,
)
from ..support import render as cli_render
import inspect


_EXPLICIT_REDUCER_ARGS = {
    "callable_id",
    "classifier_id",
    "module_id",
    "scope",
}
_RESERVED_REDUCER_ARGS = {"snapshot_id", "conn", "repo_root"}


def _reducer_callback(
    ctx: typer.Context,
    reducer_id: Optional[str] = typer.Option(
        None,
        "--id",
        help="Reducer id to render (e.g., structural_index).",
    ),
    diff_mode: str = typer.Option(
        "full",
        "--diff-mode",
        help="Diff overlay mode: full or summary.",
    ),
    callable_id: Optional[str] = typer.Option(None, "--callable-id", help="Callable id."),
    classifier_id: Optional[str] = typer.Option(
        None, "--classifier-id", help="Classifier id."
    ),
    module_id: Optional[str] = typer.Option(None, "--module-id", help="Module id."),
    scope: Optional[str] = typer.Option(
        None,
        "--scope",
        help="Scope selector for reducers that accept it (e.g., codebase, module).",
    ),
    json_flag: bool = typer.Option(
        False,
        "--json",
        help="No-op: reducer output is JSON by default.",
    ),
    **dynamic_kwargs,
) -> None:
    """Render a reducer payload (latest committed snapshot only). Prefer `--compact` when available for orientation or coupling tasks."""
    if ctx.invoked_subcommand is not None:
        return
    if not reducer_id:
        raise typer.BadParameter("Missing --id.")

    explicit_ids = {
        "callable_id": callable_id,
        "classifier_id": classifier_id,
        "module_id": module_id,
    }
    provided_ids = [name for name, value in explicit_ids.items() if value]
    if len(provided_ids) > 1:
        raise typer.BadParameter("Provide only one specific id option.")

    dynamic_params = _build_dynamic_reducer_params()
    dynamic_param_names = {param.name for param in dynamic_params}
    bool_param_names = _dynamic_bool_param_names()
    extra_args = list(ctx.args)
    arg_map = parse_extra_args(normalize_flag_args(extra_args))
    explicit_args = dict(explicit_ids)
    normalized_diff_mode = str(diff_mode or "full").strip().lower()
    if normalized_diff_mode not in {"full", "summary"}:
        raise typer.BadParameter("diff-mode must be 'full' or 'summary'.")
    explicit_args["diff_mode"] = normalized_diff_mode
    if scope:
        explicit_args["scope"] = scope
    for name, value in explicit_args.items():
        if not value:
            continue
        if name in arg_map:
            raise typer.BadParameter(f"Duplicate value for '{name}'.")
        arg_map[name] = value
    for name, value in dynamic_kwargs.items():
        if value is None:
            continue
        if name in arg_map:
            raise typer.BadParameter(f"Duplicate value for '{name}'.")
        arg_map[name] = (
            _coerce_bool_arg(name, value) if name in bool_param_names else value
        )
    _validate_reducer_args(arg_map, dynamic_param_names | set(explicit_args.keys()))
    reducer_payload, snapshot_id, resolved_args = cli_call(
        reducer_ops.emit,
        reducer_id,
        **arg_map,
    )
    warning = get_dirty_worktree_warning()
    resolution_notes = []
    if isinstance(resolved_args, dict):
        resolution_notes = resolved_args.pop("_resolution_notes", None) or []
    notes = _build_reducer_notes(reducer_id) + list(resolution_notes)
    payload = {
        "reducer_id": reducer_id,
        "snapshot_id": snapshot_id,
        "args": resolved_args,
        "payload": reducer_payload,
        "notes": notes,
    }
    if warning:
        payload["warning"] = warning
    typer.echo(json.dumps(payload))


_REDUCER_CALLBACK_BASE_SIGNATURE = inspect.signature(_reducer_callback)


def _emit_reducer_metadata_scope_warning(*, err: bool = False) -> None:
    try:
        repo_root = runtime_paths.get_repo_root()
    except api_errors.ScionaError:
        emit_user_warning(
            "Not inside a git repository; showing reducer metadata only. "
            "Identifier resolution and dirty-worktree checks are unavailable.",
            err=err,
        )
        return
    if not runtime_paths.get_sciona_dir(repo_root).exists():
        emit_user_warning(
            "SCIONA has not been initialized here; showing reducer metadata only. "
            "Run `sciona init` for identifier resolution and dirty-worktree checks.",
            err=err,
        )


def _emit_reducer_info(reducer_id: Optional[str], *, json_output: bool) -> None:
    _emit_reducer_metadata_scope_warning(err=json_output)
    if reducer_id:
        emit_dirty_worktree_warning(err=json_output)
        entry = cli_call(reducer_ops.get_entry, reducer_id)
        if json_output:
            typer.echo(json.dumps(entry))
            return
        cli_render.emit(cli_render.render_reducer_show(entry))
        return
    emit_dirty_worktree_warning(err=json_output)
    entries = cli_call(reducer_ops.list_entries)
    if json_output:
        typer.echo(json.dumps(entries))
        return
    cli_render.emit(cli_render.render_reducer_list(entries))


def _info_reducers_command(
    reducer_id: Optional[str] = typer.Option(
        None,
        "--id",
        help="Filter to a single reducer id (e.g., structural_index).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit reducer metadata as JSON instead of plain text.",
    ),
) -> None:
    """Show reducer metadata (warns if dirty)."""
    _emit_reducer_info(reducer_id, json_output=json_output)


def _list_reducers_command(
    reducer_id: Optional[str] = typer.Option(
        None,
        "--id",
        help="Filter to a single reducer id (e.g., structural_index).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit reducer metadata as JSON instead of plain text.",
    ),
) -> None:
    """List reducers with CLI call signatures and compact-mode hints (warns if dirty)."""
    _emit_reducer_metadata_scope_warning(err=json_output)
    emit_dirty_worktree_warning(err=json_output)
    entries = cli_call(reducer_ops.list_entries)
    if reducer_id:
        entries = [entry for entry in entries if entry["reducer_id"] == reducer_id]
        if not entries:
            raise typer.BadParameter(f"Unknown reducer '{reducer_id}'.")
    if json_output:
        typer.echo(json.dumps(entries))
        return
    reducers = reducer_ops.get_reducers()
    cli_render.emit(render_reducer_list(entries, reducers, include_prefix=True))


class _ReducerGroup(TyperGroup):
    """Click group that lets bool reducer options be passed as bare flags."""

    def parse_args(self, ctx, args):
        bool_flags = {
            f"--{name.replace('_', '-')}" for name in _dynamic_bool_param_names()
        }
        return super().parse_args(
            ctx, normalize_flag_args(list(args), flag_names=bool_flags)
        )


def register(app: typer.Typer) -> None:
    reducer_app = typer.Typer(
        cls=_ReducerGroup,
        help="Reducer registry helpers.",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )

    dynamic_params = _build_dynamic_reducer_params()
    _reducer_callback._base_signature = _REDUCER_CALLBACK_BASE_SIGNATURE  # type: ignore[attr-defined]
    _reducer_callback.__signature__ = _build_reducer_signature(
        _reducer_callback, dynamic_params
    )
    reducer_app.callback(invoke_without_command=True)(_reducer_callback)
    reducer_app.command("info")(_info_reducers_command)
    reducer_app.command("list")(_list_reducers_command)
    app.add_typer(reducer_app, name="reducer")


def _build_dynamic_reducer_params() -> list[inspect.Parameter]:
    params, _ = _collect_dynamic_reducer_params()
    return params


def _dynamic_bool_param_names() -> set[str]:
    _, bool_names = _collect_dynamic_reducer_params()
    return bool_names


def _collect_dynamic_reducer_params() -> tuple[list[inspect.Parameter], set[str]]:
    reducers = reducer_ops.get_reducers()
    params: dict[str, inspect.Parameter] = {}
    bool_names: set[str] = set()
    for entry in reducers.values():
        render = getattr(entry.module, "render", None)
        if render is None:
            continue
        sig = _render_signature(render)
        for name, param in sig.parameters.items():
            if name in _RESERVED_REDUCER_ARGS or name in _EXPLICIT_REDUCER_ARGS:
                continue
            if param.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                continue
            if name in params:
                continue
            is_bool = (
                name == "extras"
                or _extract_primitive_type(param.annotation) is bool
            )
            if is_bool:
                bool_names.add(name)
            # Bool params register as value-taking str options: typer cannot
            # model optional-value options, so bare usage is normalized by
            # _ReducerGroup and values are coerced in the callback.
            option_type = (
                Optional[str] if is_bool else _infer_option_type(name, param)
            )
            params[name] = inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=typer.Option(None),
                annotation=option_type,
            )
    return [params[name] for name in sorted(params.keys())], bool_names


def _render_signature(render) -> inspect.Signature:
    try:
        return inspect.signature(render, eval_str=True)
    except Exception:
        return inspect.signature(render)


def _infer_option_type(name: str, param: inspect.Parameter):
    if name == "extras":
        return Optional[bool]
    annotation = param.annotation
    primitive = _extract_primitive_type(annotation)
    return Optional[primitive or str]


def _extract_primitive_type(annotation):
    if annotation in {str, int, float, bool}:
        return annotation
    origin = get_origin(annotation)
    if origin is None:
        return None
    if origin in {list, dict, set, tuple}:
        return None
    if origin is Union or origin is types.UnionType:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1 and args[0] in {str, int, float, bool}:
            return args[0]
    return None


def _build_reducer_signature(
    func, dynamic_params: list[inspect.Parameter]
) -> inspect.Signature:
    sig = getattr(func, "_base_signature", _REDUCER_CALLBACK_BASE_SIGNATURE)
    base_params = [
        param
        for param in sig.parameters.values()
        if param.kind is not inspect.Parameter.VAR_KEYWORD
    ]
    return sig.replace(parameters=[*base_params, *dynamic_params])


def _validate_reducer_args(arg_map: dict[str, object], allowed: set[str]) -> None:
    for name in arg_map.keys():
        if name not in allowed:
            raise typer.BadParameter(f"Unknown reducer parameter '{name}'.")


_BOOL_TRUE_VALUES = frozenset({"true", "1", "yes"})
_BOOL_FALSE_VALUES = frozenset({"false", "0", "no"})


def _coerce_bool_arg(name: str, value: object) -> bool:
    normalized = str(value).strip().lower()
    if normalized in _BOOL_TRUE_VALUES:
        return True
    if normalized in _BOOL_FALSE_VALUES:
        return False
    raise typer.BadParameter(
        f"Expected a boolean for '--{name.replace('_', '-')}', got '{value}'."
    )


def _build_reducer_notes(reducer_id: str) -> list[str]:
    return ["[tool limitation] Results reflect the latest committed snapshot only."]
