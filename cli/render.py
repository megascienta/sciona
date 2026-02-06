"""CLI render helpers for human-readable output."""

from __future__ import annotations

from typing import Iterable


def render_init(payload: dict) -> list[str]:
    lines = [f"Initialized SCIONA in {payload['sciona_dir']}"]
    if not payload.get("iterative"):
        lines.extend(
            [
                "Notes:",
                "  - SCIONA analyzes only git-tracked files",
                "  - Ensure '.sciona/' is not committed to version control",
            ]
        )
    else:
        config_path = payload.get("config_path")
        lines.extend(
            [
                "Warning:",
                f"  Edit config: {config_path}",
                "  Enable languages, then run: sciona build",
            ]
        )
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


def render_discovery_summary(payload: dict) -> list[str]:
    enabled = list(payload.get("enabled_languages") or [])
    counts = payload.get("discovery_counts") or {}
    candidates = payload.get("discovery_candidates") or {}
    excluded_total = payload.get("discovery_excluded_total", 0) or 0
    excluded_by_glob = payload.get("discovery_excluded_by_glob") or {}
    exclude_globs = payload.get("exclude_globs") or []
    lines: list[str] = []
    if enabled:
        lines.append("Discovery summary:")
        for language in enabled:
            count = counts.get(language, 0)
            suffix = " (enabled)" if count == 0 else ""
            lines.append(f"  {language}: {count} files{suffix}")
        lines.append("Source candidates by extension:")
        for language in enabled:
            lines.append(f"  {language}: {candidates.get(language, 0)}")
    if excluded_total:
        lines.append(f"Excluded by discovery filters: {excluded_total}")
        for pattern, count in excluded_by_glob.items():
            lines.append(f"  {pattern}: {count}")
    if exclude_globs:
        lines.append("Discovery filters active:")
        lines.append("  exclude_globs:")
        for entry in exclude_globs:
            lines.append(f"    - {entry}")
    return lines


def render_build(payload: dict) -> list[str]:
    lines = []
    lines.extend(render_discovery_summary(payload))
    lines.append(f"Files analyzed: {payload['files_processed']}")
    lines.append(f"Structural nodes updated: {payload['nodes_recorded']}")
    if payload.get("parse_failures"):
        lines.append("Analysis warnings:")
        lines.append(
            f"  - {payload['parse_failures']} files failed to parse (partial snapshot)"
        )
        lines.append("Run with --debug for details.")
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
    if payload.get("enabled_languages") is not None:
        lines.append("Discovery:")
        enabled = payload.get("enabled_languages") or []
        if enabled:
            for language in enabled:
                lines.append(f"  Enabled: {language}")
        else:
            lines.append("  Enabled: none")
        exclude_count = payload.get("exclude_globs_count", 0) or 0
        if exclude_count:
            lines.append(f"  Exclude globs: {exclude_count} pattern(s)")
            for entry in payload.get("exclude_globs", []) or []:
                lines.append(f"    - {entry}")
        else:
            lines.append("  Exclude globs: none")
    last_build = payload.get("last_build")
    if last_build:
        lines.append("Last build:")
        lines.append(f"  Snapshot: {last_build.get('snapshot_id')}")
        if last_build.get("created_at") is not None:
            lines.append(f"  Created: {_format_ts(last_build.get('created_at'))}")
        lines.append(f"  Files analyzed: {last_build.get('files_processed')}")
        langs = last_build.get("enabled_languages") or []
        if langs:
            lines.append(f"  Languages: {', '.join(langs)}")
        counts = last_build.get("discovery_counts") or {}
        if counts:
            lines.append("  Discovery summary:")
            for language in langs:
                lines.append(f"    {language}: {counts.get(language, 0)}")
    return lines


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
    lines = ["Available reducers:"]
    for entry in sorted(entries, key=lambda item: (item["scope"], item["reducer_id"])):
        lines.append(f"- {entry['reducer_id']}: {entry['summary']}")
    return lines


def render_reducer_show(entry: dict) -> list[str]:
    lines = [
        f"Reducer: {entry['reducer_id']}",
        f"Scope: {entry['scope']}",
        f"Semantic tag: {entry['semantic_tag']}",
        f"Determinism: {entry['determinism']}",
        "",
        "Summary:",
        f"  {entry['summary']}",
    ]
    return lines
