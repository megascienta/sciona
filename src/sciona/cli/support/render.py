# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CLI render helpers for human-readable output."""

from __future__ import annotations

from typing import Iterable

from ...runtime.reducers.listing import (
    render_reducer_catalog,
)


def _format_status_timestamp(value: object) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip()
    return text or "unknown"


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
    if str(payload.get("status") or "") == "reused":
        return []
    lines: list[str] = []
    report = payload.get("report")
    command_wall_seconds = _format_duration_seconds(payload.get("command_wall_seconds"))
    if report:
        report_payload = dict(report)
        report_payload["artifact_db_available"] = bool(
            payload.get("artifact_db_available", False)
        )
        lines.append("Summary:")
        timing = report_payload.get("timing") or {}
        displayed_total = command_wall_seconds or _format_duration_seconds(
            timing.get("build_total_seconds")
        )
        if displayed_total is not None:
            lines.append(f"  Wall time: {displayed_total}")
        build_total_seconds = _format_duration_seconds(timing.get("build_total_seconds"))
        if (
            command_wall_seconds is not None
            and build_total_seconds is not None
        ):
            lines.append(f"  Core build time: {build_total_seconds}")
            lines.extend(
                _render_summary_lines(
                report_payload,
                    indent="  ",
                    include_reasons=False,
                    include_call_stats=False,
                    include_scope_split=False,
                )
        )
    else:
        lines.append("Summary: unavailable")
    return lines


def render_status(payload: dict) -> list[str]:
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
            f"  Latest: {payload['latest_snapshot']} @ {_format_status_timestamp(payload.get('latest_created'))}"
        )
    lines.append(f"  Database present: {'yes' if payload['db_exists'] else 'no'}")
    report = payload.get("report")
    if payload.get("latest_snapshot"):
        lines.append("Last build:")
        if report:
            build_health = str(payload.get("build_health") or "").strip()
            if build_health == "degraded":
                detail_parts: list[str] = []
                parse_failures = payload.get("parse_failures")
                if parse_failures is not None:
                    detail_parts.append(f"parse_failures={int(parse_failures or 0)}")
                residual_containment_failures = payload.get(
                    "residual_containment_failures"
                )
                if residual_containment_failures is not None:
                    detail_parts.append(
                        "residual_containment_failures="
                        f"{int(residual_containment_failures or 0)}"
                    )
                detail_text = f" ({', '.join(detail_parts)})" if detail_parts else ""
                lines.append(f"  Health: degraded{detail_text}")
            report_payload = dict(report)
            report_payload["artifact_db_available"] = bool(
                payload.get("artifact_db_available", False)
            )
            timing = report_payload.get("timing") or {}
            build_wall_seconds = _format_duration_seconds(
                timing.get("build_wall_seconds")
            )
            build_total_seconds = _format_duration_seconds(
                timing.get("build_total_seconds")
            )
            if build_wall_seconds is not None:
                lines.append(f"  Wall time: {build_wall_seconds}")
            elif build_total_seconds is not None:
                lines.append(f"  Core build time: {build_total_seconds}")
            if (
                build_wall_seconds is not None
                and build_total_seconds is not None
            ):
                lines.append(f"  Core build time: {build_total_seconds}")
            lines.append("  Summary:")
            lines.extend(
                _render_summary_lines(
                    report_payload,
                    indent="    ",
                    include_reasons=bool(payload.get("detailed")),
                    include_call_stats=bool(payload.get("detailed")),
                    include_scope_split=bool(payload.get("detailed")),
                )
            )
        else:
            lines.append("  Summary: unavailable")
    return lines


def _format_duration_seconds(value: object) -> str | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return f"{seconds:.2f}s"


def _render_summary_lines(
    summary: dict,
    *,
    indent: str,
    include_reasons: bool,
    include_call_stats: bool = True,
    include_scope_split: bool = False,
) -> list[str]:
    lines: list[str] = []
    timing = summary.get("timing") or {}
    scopes = summary.get("scopes") or {}
    for language, item in (summary.get("languages") or {}).items():
        language = str(language or "unknown")
        structure = item.get("structure") or {}
        lines.append(f"{indent}{language}: {_format_structure_summary(structure)}")
        if include_call_stats:
            callsites = item.get("callsites") or {}
            callsites_text = _format_callsites_summary(callsites)
            if callsites_text:
                lines.append(f"{indent}  callsites: {callsites_text}")
            materialization = item.get("call_materialization") or {}
            materialization_text = _format_call_materialization_summary(materialization)
            if materialization_text:
                lines.append(f"{indent}  call_materialization: {materialization_text}")
        if include_reasons:
            filtered = item.get("not_accepted_callsites") or {}
            filtered_text = _format_pre_persist_filter_summary(filtered)
            if filtered_text:
                lines.append(f"{indent}  not_accepted_callsites: {filtered_text}")
    totals = summary.get("totals") or {}
    totals_structure = totals.get("structure") or {}
    lines.append(f"{indent}total: {_format_structure_summary(totals_structure)}")
    if include_call_stats:
        totals_callsites = totals.get("callsites") or {}
        totals_callsites_text = _format_callsites_summary(totals_callsites)
        if totals_callsites_text:
            lines.append(f"{indent}  callsites: {totals_callsites_text}")
        totals_materialization = totals.get("call_materialization") or {}
        totals_materialization_text = _format_call_materialization_summary(
            totals_materialization
        )
        if totals_materialization_text:
            lines.append(
                f"{indent}  call_materialization: {totals_materialization_text}"
            )
    if include_reasons:
        totals_filtered = totals.get("not_accepted_callsites") or {}
        totals_filtered_text = _format_pre_persist_filter_summary(totals_filtered)
        if totals_filtered_text:
            lines.append(f"{indent}  not_accepted_callsites: {totals_filtered_text}")
    if include_scope_split:
        lines.extend(_render_scope_lines(scopes, indent=f"{indent}"))
    if not summary.get("artifact_db_available", False):
        lines.append(f"{indent}call diagnostics: unavailable (artifact DB missing)")
    phase_timings = timing.get("build_phase_timings") or {}
    if include_reasons and phase_timings:
        lines.append(f"{indent}build phases:")
        for phase, seconds in phase_timings.items():
            duration = _format_duration_seconds(seconds)
            if duration is None:
                continue
            lines.append(f"{indent}  {phase}: {duration}")
    return lines


def _format_structure_summary(structure: dict) -> str:
    files = int(structure.get("files") or 0)
    nodes = int(structure.get("nodes") or 0)
    edges = structure.get("edges")
    edges_text = "n/a" if edges is None else str(int(edges or 0))
    return f"{files} files, {nodes} nodes, {edges_text} edges"


def _format_callsites_summary(callsites: dict) -> str:
    observed = callsites.get("observed_syntactic_callsites")
    accepted = callsites.get("accepted_callsites")
    not_accepted = callsites.get("not_accepted_callsites")
    if all(value is None for value in (observed, accepted, not_accepted)):
        return ""
    return (
        f"observed={int(observed or 0)}, accepted={int(accepted or 0)}, "
        f"not_accepted={int(not_accepted or 0)}"
    )


def _format_call_materialization_summary(materialization: dict) -> str:
    edges = materialization.get("finalized_call_edges")
    if edges is None:
        return ""
    return f"finalized_call_edges={int(edges or 0)}"


def _format_pre_persist_filter_summary(filtered: dict) -> str:
    if not filtered:
        return ""
    return ", ".join(f"{name}={int(count or 0)}" for name, count in filtered.items())


def _render_scope_lines(
    scopes: dict[str, dict[str, object]] | None,
    *,
    indent: str,
) -> list[str]:
    if not scopes:
        return []
    lines: list[str] = []
    for scope_key in ("non_tests", "tests"):
        scope = scopes.get(scope_key) or {}
        structure = scope.get("structure")
        callsites = scope.get("callsites") or {}
        materialization = scope.get("call_materialization") or {}
        filtered = scope.get("not_accepted_callsites") or {}
        structure_text = (
            _format_structure_summary(structure)
            if isinstance(structure, dict)
            else ""
        )
        callsites_text = _format_callsites_summary(callsites)
        materialization_text = _format_call_materialization_summary(materialization)
        filtered_text = _format_pre_persist_filter_summary(filtered)
        lines.append(f"{indent}{scope_key}:")
        if structure_text:
            lines.append(f"{indent}  structure: {structure_text}")
        if callsites_text:
            lines.append(f"{indent}  callsites: {callsites_text}")
        if materialization_text:
            lines.append(f"{indent}  call_materialization: {materialization_text}")
        if filtered_text:
            lines.append(f"{indent}  not_accepted_callsites: {filtered_text}")
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
    return render_reducer_catalog(entries)


def render_reducer_show(entry: dict) -> list[str]:
    summary = str(entry["summary"])
    lines = [
        f"Reducer: {entry['reducer_id']}",
        f"Category: {entry['category']}",
        f"Placeholder: {entry['placeholder']}",
        "",
        "Summary:",
        f"  {summary}",
    ]
    return lines
