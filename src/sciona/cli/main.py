# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""SCIONA command-line interface."""

from __future__ import annotations

import typer
import click

import inspect

from ..api import cli as api_cli
from ..api import errors as api_errors
from .commands import register as register_commands
from ..runtime.common.constants import TOOL_VERSION


def _patch_click_make_metavar() -> None:
    sig = inspect.signature(click.Parameter.make_metavar)
    if "ctx" not in sig.parameters:
        _patch_typer_argument_make_metavar()
        return
    if sig.parameters["ctx"].default is not inspect._empty:
        _patch_typer_argument_make_metavar()
        return
    original = click.Parameter.make_metavar

    def _make_metavar(self, ctx=None):
        return original(self, ctx)

    click.Parameter.make_metavar = _make_metavar  # type: ignore[assignment]
    _patch_typer_argument_make_metavar()


def _patch_typer_argument_make_metavar() -> None:
    try:
        import typer.core as typer_core
    except Exception:
        return
    typer_arg = getattr(typer_core, "TyperArgument", None)
    if typer_arg is None:
        return
    sig = inspect.signature(typer_arg.make_metavar)
    if "ctx" in sig.parameters:
        return

    def _make_metavar(self, ctx=None):
        if self.metavar is not None:
            return self.metavar
        var = (self.name or "").upper()
        if not self.required:
            var = f"[{var}]"
        try:
            type_var = self.type.get_metavar(self, ctx)
        except TypeError:
            type_var = self.type.get_metavar(self)
        if type_var:
            var += f":{type_var}"
        if self.nargs != 1:
            var += "..."
        return var

    typer_arg.make_metavar = _make_metavar  # type: ignore[assignment]


_patch_click_make_metavar()

app = typer.Typer(
    help=(
        "[bold]SCIONA[/bold] builds a deterministic structural index (SCI) of a Git repository."
        "It records what exists in code—modules, classifiers, and callables—and how "
        "these entities are structurally connected. The result is an explicit, "
        "machine-readable representation of code structure. "
        "[bold]SCIONA[/bold] is designed to anchor LLM-assisted workflows: downstream tools can "
        "reason over deterministic structure instead of heuristically inferring it "
        "from source text or hallucinating missing connections."
    ),
    rich_markup_mode="rich",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", is_eager=True, help="Show version and exit."
    ),
) -> None:
    """CLI entrypoint."""
    if version:
        typer.echo(TOOL_VERSION)
        raise typer.Exit()
    repo_root = None
    try:
        repo_root = api_cli.get_repo_root()
        logging_settings = api_cli.load_logging_settings(
            repo_root,
            allow_missing=True,
        )
        api_cli.configure_logging(
            level=logging_settings.level,
            module_levels=logging_settings.module_levels,
            debug=logging_settings.debug,
            structured=logging_settings.structured,
            repo_root=repo_root,
        )
    except api_errors.ScionaError:
        api_cli.configure_logging()
    api_cli.freeze_registry()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _core_commands(
    cli_app: typer.Typer,
    root_group: click.Group,
) -> list[str]:
    commands = _command_names(cli_app)
    entries: list[str] = []
    for name in commands:
        cmd = _get_command(root_group, name)
        entries.append(f"{name}{_format_params(cmd)}")
    return entries


def _group_commands(
    cli_app: typer.Typer,
    group_name: str,
    root_group: click.Group,
    *,
    include_root_options: bool = True,
) -> list[str]:
    if isinstance(root_group, click.Group):
        root_cmd = root_group.commands.get(group_name)
        if isinstance(root_cmd, click.Group):
            entries: list[str] = []
            root_params = _format_params(root_cmd) if include_root_options else ""
            if root_params:
                entries.append(f"{group_name}{root_params}")
            for name, cmd in root_cmd.commands.items():
                if getattr(cmd, "hidden", False):
                    continue
                entries.append(f"{group_name} {name}{_format_params(cmd)}")
            return entries
    group = _find_group(cli_app, group_name)
    if group is None:
        return []
    group_cmd = _get_click_group(group)
    if not isinstance(group_cmd, click.Group):
        return [f"{group_name} {name}" for name in _command_names(group)]
    entries: list[str] = []
    root_params = _format_params(group_cmd) if include_root_options else ""
    if root_params:
        entries.append(f"{group_name}{root_params}")
    for name in _command_names(group):
        cmd = group_cmd.commands.get(name)
        if cmd is None:
            entries.append(f"{group_name} {name}")
            continue
        if getattr(cmd, "hidden", False):
            continue
        rendered = _format_params(cmd)
        entries.append(f"{group_name} {name}{rendered}")
    return entries


def _find_group(cli_app: typer.Typer, group_name: str) -> typer.Typer | None:
    for info in getattr(cli_app, "registered_groups", []) or []:
        name = getattr(info, "name", None)
        if name != group_name:
            continue
        return getattr(info, "typer_instance", None)
    return None


def _command_names(cli_app: typer.Typer) -> list[str]:
    names: list[str] = []
    for info in getattr(cli_app, "registered_commands", []) or []:
        name = getattr(info, "name", None)
        if not name:
            callback = getattr(info, "callback", None)
            if callback is not None:
                name = callback.__name__.replace("_", "-")
        if name:
            names.append(name)
    return names


def _get_click_group(cli_app: typer.Typer) -> click.Group:
    return typer.main.get_command(cli_app)


def _get_command(root_group: click.Group, name: str) -> click.Command | None:
    if not isinstance(root_group, click.Group):
        return None
    return root_group.commands.get(name)


def _format_params(cmd: click.Command | None, *, include_arguments: bool = True) -> str:
    if cmd is None:
        return ""
    arguments = []
    options = []
    for param in getattr(cmd, "params", []) or []:
        if isinstance(param, click.Argument):
            if include_arguments:
                arg = _primary_argument(param)
                if arg:
                    arguments.append(arg)
            continue
        if isinstance(param, click.Option):
            opt = _primary_option(param)
            if opt:
                options.append(opt)
    if not arguments and not options:
        return ""
    rendered = []
    rendered.extend(arguments)
    rendered.extend(f"[{opt}]" for opt in options)
    return " " + " ".join(rendered)


def _primary_option(option: click.Option) -> str:
    opts = list(option.opts) + list(option.secondary_opts)
    if not opts:
        return ""
    long_opts = [opt for opt in opts if opt.startswith("--")]
    opt = long_opts[0] if long_opts else opts[0]
    if option.is_flag or option.count:
        return opt
    metavar = option.metavar
    if not metavar:
        name = option.name or ""
        metavar = name.replace("-", "_").upper() if name else ""
    if metavar:
        return f"{opt} {metavar}"
    return opt


def _primary_argument(argument: click.Argument) -> str:
    name = argument.metavar or argument.name or ""
    label = name.replace("-", "_").upper() if name else "ARG"
    if argument.nargs != 1:
        label = f"{label}..."
    return label


register_commands(app)


def run() -> None:
    app()


from .surfaces.reducer import register as register_reducer  # noqa: E402
from .surfaces.resolve import register as register_resolve  # noqa: E402
from .surfaces.search import register as register_search  # noqa: E402

register_reducer(app)
register_resolve(app)
register_search(app)

if __name__ == "__main__":
    run()
