# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer commands."""

from __future__ import annotations

from typing import Optional, Union, get_args, get_origin

import json

import typer

from ...api import cli as reducer_api
from ...runtime.reducers.listing import render_reducer_list
from ..utils import (
    cli_call,
    emit_dirty_worktree_warning,
    get_dirty_worktree_warning,
    normalize_flag_args,
    parse_extra_args,
)
from .. import render as cli_render
import inspect


_EXPLICIT_REDUCER_ARGS = {
    "callable_id",
    "classifier_id",
    "module_id",
    "scope",
}
_RESERVED_REDUCER_ARGS = {"snapshot_id", "conn", "repo_root"}


def register(app: typer.Typer) -> None:
    reducer_app = typer.Typer(
        help="Reducer registry helpers.",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )

    dynamic_params = _build_dynamic_reducer_params()
    dynamic_param_names = {param.name for param in dynamic_params}

    @reducer_app.callback(
        invoke_without_command=True,
    )
    def reducer(
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
        callable_id: Optional[str] = typer.Option(
            None, "--callable-id", help="Callable id."
        ),
        classifier_id: Optional[str] = typer.Option(
            None, "--classifier-id", help="Classifier id."
        ),
        module_id: Optional[str] = typer.Option(None, "--module-id", help="Module id."),
        scope: Optional[str] = typer.Option(
            None,
            "--scope",
            help="Scope selector for reducers that accept it (e.g., codebase, module).",
        ),
        **dynamic_kwargs,
    ) -> None:
        """Render a reducer payload (latest committed snapshot only). Example: sciona reducer --id structural_index"""
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
            arg_map[name] = value
        _validate_reducer_args(arg_map, dynamic_param_names | set(explicit_args.keys()))
        reducer_payload, snapshot_id, resolved_args = cli_call(
            reducer_api.emit,
            reducer_id,
            **arg_map,
        )
        warning = get_dirty_worktree_warning()
        notes = _build_reducer_notes(reducer_id)
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

    reducer.__signature__ = _build_reducer_signature(reducer, dynamic_params)

    def _emit_reducer_info(reducer_id: Optional[str]) -> None:
        if reducer_id:
            emit_dirty_worktree_warning()
            entry = cli_call(reducer_api.get_entry, reducer_id)
            cli_render.emit(cli_render.render_reducer_show(entry))
            return
        emit_dirty_worktree_warning()
        entries = cli_call(reducer_api.list_entries)
        cli_render.emit(cli_render.render_reducer_list(entries))

    @reducer_app.command("info")
    def info_reducers(
        reducer_id: Optional[str] = typer.Option(
            None,
            "--id",
            help="Filter to a single reducer id (e.g., structural_index).",
        ),
    ) -> None:
        """Show reducer metadata (warns if dirty)."""
        _emit_reducer_info(reducer_id)

    @reducer_app.command("list")
    def list_reducers(
        reducer_id: Optional[str] = typer.Option(
            None,
            "--id",
            help="Filter to a single reducer id (e.g., structural_index).",
        ),
    ) -> None:
        """List reducers with CLI call signatures (warns if dirty)."""
        emit_dirty_worktree_warning()
        entries = cli_call(reducer_api.list_entries)
        if reducer_id:
            entries = [entry for entry in entries if entry["reducer_id"] == reducer_id]
            if not entries:
                raise typer.BadParameter(f"Unknown reducer '{reducer_id}'.")
        reducers = reducer_api.get_reducers()
        cli_render.emit(render_reducer_list(entries, reducers, include_prefix=True))

    app.add_typer(reducer_app, name="reducer")


def _build_dynamic_reducer_params() -> list[inspect.Parameter]:
    reducers = reducer_api.get_reducers()
    params: dict[str, inspect.Parameter] = {}
    for entry in reducers.values():
        render = getattr(entry.module, "render", None)
        if render is None:
            continue
        sig = inspect.signature(render)
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
            option_type = _infer_option_type(name, param)
            params[name] = inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=typer.Option(None),
                annotation=option_type,
            )
    return [params[name] for name in sorted(params.keys())]


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
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1 and args[0] in {str, int, float, bool}:
            return args[0]
    return None


def _build_reducer_signature(
    func, dynamic_params: list[inspect.Parameter]
) -> inspect.Signature:
    sig = inspect.signature(func)
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


def _build_reducer_notes(reducer_id: str) -> list[str]:
    return ["[tool limitation] Results reflect the latest committed snapshot only."]
