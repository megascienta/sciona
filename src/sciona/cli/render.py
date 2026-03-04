# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI render helpers for human-readable output."""

from __future__ import annotations

from typing import Iterable

from ..runtime.reducer_listing import render_reducer_catalog


def render_init(payload: dict) -> list[str]:
    lines = [f"Initialized SCIONA in {payload['sciona_dir']}"]
    if payload.get("iterative"):
        return lines
    lines.extend(
        [
            "Next steps:",
            "  1. Edit .sciona/config.yaml",
            "  2. Enable at least one language, for example:",
            "     languages:",
            "       python:",
            "         enabled: true",
            "  3. Run: sciona build",
        ]
    )
    return lines


def render_build(payload: dict) -> list[str]:
    lines: list[str] = []
    summary = payload.get("summary")
    if summary:
        lines.append("Summary:")
        lines.extend(_render_summary_lines(summary, indent="  ", include_reasons=False))
    else:
        lines.append("Summary: unavailable")
    return lines


def render_status(payload: dict) -> list[str]:
    def _format_ts(value: object) -> str:
        if value is None:
            return "unknown"
        text = str(value).strip()
        return text or "unknown"

    lines = [
        "Repository:",
        f"  Path: {payload['repo_root']}",
        f"  Tool version: {payload['tool_version']}",
        f"  Schema version: {payload['schema_version']}",
    ]
    lines.append("Snapshots:")
    lines.append(f"  Committed: {payload['snapshot_count']}")
    if payload.get("latest_snapshot"):
        lines.append(
            f"  Latest: {payload['latest_snapshot']} @ {_format_ts(payload.get('latest_created'))}"
        )
    lines.append(f"  Database present: {'yes' if payload['db_exists'] else 'no'}")
    summary = payload.get("summary")
    if payload.get("latest_snapshot"):
        lines.append("Last build:")
        if summary:
            lines.append("  Summary:")
            lines.extend(
                _render_summary_lines(
                    summary,
                    indent="    ",
                    include_reasons=bool(payload.get("detailed")),
                )
            )
        else:
            lines.append("  Summary: unavailable")
    return lines


def _render_summary_lines(
    summary: dict,
    *,
    indent: str,
    include_reasons: bool,
) -> list[str]:
    lines: list[str] = []
    for item in summary.get("languages", []) or []:
        language = str(item.get("language") or "unknown")
        files = int(item.get("files") or 0)
        nodes = int(item.get("nodes") or 0)
        edges = int(item.get("edges") or 0)
        lines.append(
            f"{indent}{language}: {files} files, {nodes} nodes, {edges} edges, "
            f"{_format_call_site_summary(item.get('call_sites') or {})}"
        )
        if include_reasons:
            reasons = item.get("drop_reasons") or {}
            if reasons:
                reason_text = ", ".join(
                    f"{name}={count}" for name, count in sorted(reasons.items())
                )
                lines.append(f"{indent}  failed reasons: {reason_text}")
    totals = summary.get("totals") or {}
    total_files = int(totals.get("files") or 0)
    total_nodes = int(totals.get("nodes") or 0)
    total_edges = int(totals.get("edges") or 0)
    lines.append(
        f"{indent}total: {total_files} files, {total_nodes} nodes, {total_edges} edges, "
        f"{_format_call_site_summary(totals.get('call_sites') or {})}"
    )
    if not summary.get("artifact_db_available", False):
        lines.append(f"{indent}call_sites diagnostics: unavailable (artifact DB missing)")
    return lines


def _format_call_site_summary(call_sites: dict) -> str:
    eligible = call_sites.get("eligible")
    accepted = call_sites.get("accepted")
    dropped = call_sites.get("dropped")
    rate = call_sites.get("success_rate")
    if eligible is None or accepted is None or dropped is None:
        return "call_sites: n/a"
    if eligible == 0:
        return "call_sites: n/a (0/0), failed: 0"
    percentage = float(rate or 0.0) * 100.0
    return (
        f"call_sites: {percentage:.1f}% successful ({accepted}/{eligible}), "
        f"failed: {dropped}"
    )


def emit(lines: Iterable[str]) -> None:
    import typer

    for line in lines:
        typer.echo(line)


def render_error(message: str) -> list[str]:
    return message.splitlines() if message else []


def emit_error(lines: Iterable[str]) -> None:
    import typer

    for index, line in enumerate(lines):
        if index == 0 and line and not line.startswith("Error:"):
            line = f"Error: {line}"
        typer.secho(line, fg=typer.colors.RED)


def emit_warning(lines: Iterable[str]) -> None:
    import typer

    for index, line in enumerate(lines):
        if index == 0 and line and not line.startswith("Warning:"):
            line = f"Warning: {line}"
        typer.secho(line, fg=typer.colors.YELLOW)


def render_reducer_list(entries: list[dict]) -> list[str]:
    return render_reducer_catalog(entries)


def render_reducer_show(entry: dict) -> list[str]:
    lines = [
        f"Reducer: {entry['reducer_id']}",
        f"Scope: {entry['scope']}",
        f"Category: {entry['category']}",
        f"Determinism: {entry['determinism']}",
        "",
        "Summary:",
        f"  {entry['summary']}",
    ]
    return lines
