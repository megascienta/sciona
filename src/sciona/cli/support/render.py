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
    lines: list[str] = []
    summary = payload.get("summary")
    command_wall_seconds = _format_duration_seconds(payload.get("command_wall_seconds"))
    if summary:
        lines.append("Summary:")
        displayed_total = command_wall_seconds or _format_duration_seconds(
            summary.get("build_total_seconds")
        )
        if displayed_total is not None:
            lines.append(f"  Wall time: {displayed_total}")
        build_total_seconds = _format_duration_seconds(summary.get("build_total_seconds"))
        if (
            command_wall_seconds is not None
            and build_total_seconds is not None
        ):
            lines.append(f"  Core build time: {build_total_seconds}")
        lines.extend(
            _render_summary_lines(
                summary,
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
    summary = payload.get("summary")
    if payload.get("latest_snapshot"):
        lines.append("Last build:")
        if summary:
            build_wall_seconds = _format_duration_seconds(
                summary.get("build_wall_seconds")
            )
            build_total_seconds = _format_duration_seconds(summary.get("build_total_seconds"))
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
                    summary,
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
    for item in summary.get("languages", []) or []:
        language = str(item.get("language") or "unknown")
        files = int(item.get("files") or 0)
        nodes = int(item.get("nodes") or 0)
        edges = int(item.get("edges") or 0)
        lines.append(f"{indent}{language}: {files} files, {nodes} nodes, {edges} edges")
        if include_call_stats:
            lines.append(
                f"{indent}  callsite_pairs: "
                f"{_format_count_summary(item.get('callsite_pairs') or {}, label='pairs')}"
            )
            lines.append(
                f"{indent}  finalized_call_edges: "
                f"{_format_count_summary(item.get('finalized_call_edges') or {}, label='edges')}"
            )
            funnel = item.get("call_site_funnel") or {}
            funnel_text = _format_call_site_funnel_summary(funnel)
            if funnel_text:
                lines.append(f"{indent}  call_funnel: {funnel_text}")
            if include_scope_split:
                lines.extend(
                    _render_scope_count_lines(
                        item.get("callsite_pairs_by_scope"),
                        item.get("finalized_call_edges_by_scope"),
                        indent=f"{indent}    ",
                    )
                )
        if include_reasons:
            filtered = item.get("filtered_pre_persist_buckets") or {}
            if filtered:
                filtered_text = ", ".join(
                    f"{name}={count}" for name, count in sorted(filtered.items())
                )
                lines.append(f"{indent}  filtered_pre_persist: {filtered_text}")
        density = item.get("structural_density") or {}
        if density.get("inflation_warning"):
            lines.append(
                f"{indent}  warning: low-node file ratio is high "
                f"({float(density.get('low_node_file_ratio') or 0.0):.1%})"
            )
    totals = summary.get("totals") or {}
    total_files = int(totals.get("files") or 0)
    total_nodes = int(totals.get("nodes") or 0)
    total_edges = int(totals.get("edges") or 0)
    lines.append(f"{indent}total: {total_files} files, {total_nodes} nodes, {total_edges} edges")
    if include_call_stats:
        lines.append(
            f"{indent}  callsite_pairs: "
            f"{_format_count_summary(totals.get('callsite_pairs') or {}, label='pairs')}"
        )
        lines.append(
            f"{indent}  finalized_call_edges: "
            f"{_format_count_summary(totals.get('finalized_call_edges') or {}, label='edges')}"
        )
        funnel = totals.get("call_site_funnel") or {}
        funnel_text = _format_call_site_funnel_summary(funnel)
        if funnel_text:
            lines.append(f"{indent}  call_funnel: {funnel_text}")
        if include_scope_split:
            lines.extend(
                _render_scope_count_lines(
                    totals.get("callsite_pairs_by_scope"),
                    totals.get("finalized_call_edges_by_scope"),
                    indent=f"{indent}    ",
                )
            )
    if include_reasons:
        filtered = totals.get("filtered_pre_persist_buckets") or {}
        if filtered:
            filtered_text = ", ".join(
                f"{name}={count}" for name, count in sorted(filtered.items())
            )
            lines.append(f"{indent}  filtered_pre_persist: {filtered_text}")
    totals_density = totals.get("structural_density") or {}
    if totals_density.get("inflation_warning"):
        lines.append(
            f"{indent}  warning: low-node file ratio is high "
            f"({float(totals_density.get('low_node_file_ratio') or 0.0):.1%})"
        )
    if not summary.get("artifact_db_available", False):
        lines.append(f"{indent}call_sites diagnostics: unavailable (artifact DB missing)")
    return lines


def _format_count_summary(payload: dict, *, label: str) -> str:
    count = payload.get("count")
    if count is None:
        return f"{label}: n/a"
    return f"{label}: {int(count)}"


def _format_call_site_funnel_summary(call_site_funnel: dict) -> str:
    observed = call_site_funnel.get("observed_syntactic_callsites")
    filtered = call_site_funnel.get("filtered_pre_persist")
    persisted = call_site_funnel.get("persisted_callsites")
    accepted = call_site_funnel.get("persisted_accepted")
    dropped = call_site_funnel.get("persisted_dropped")
    if any(value is None for value in (observed, filtered, persisted, accepted, dropped)):
        return ""
    conservation = call_site_funnel.get("conservation_ok")
    suffix = ""
    if conservation is False:
        suffix = " [conservation mismatch]"
    return (
        f"observed={observed}, filtered_pre_persist={filtered}, "
        f"persisted={persisted}, accepted={accepted}, dropped={dropped}{suffix}"
    )


def _render_name_collision_diagnostics(payload: dict, *, indent: str) -> list[str]:
    detected = int(payload.get("name_collisions_detected") or 0)
    disambiguated = int(payload.get("name_collisions_disambiguated") or 0)
    residual = int(payload.get("residual_containment_failures") or 0)
    by_language = payload.get("name_collisions_by_language") or {}
    if detected == 0 and disambiguated == 0 and residual == 0:
        return []
    lines = [
        f"{indent}name_collisions_detected: {detected}",
        f"{indent}name_collisions_disambiguated: {disambiguated}",
        f"{indent}residual_containment_failures: {residual}",
    ]
    for language in sorted(by_language):
        item = by_language.get(language) or {}
        lang_detected = int(item.get("name_collisions_detected") or 0)
        lang_disambiguated = int(item.get("name_collisions_disambiguated") or 0)
        lines.append(
            f"{indent}{language}: detected={lang_detected}, disambiguated={lang_disambiguated}"
        )
    return lines


def _render_import_diagnostics(payload: dict, *, indent: str) -> list[str]:
    seen = int(payload.get("imports_seen") or 0)
    internal = int(payload.get("imports_internal") or 0)
    filtered = int(payload.get("imports_filtered_not_internal") or 0)
    by_language = payload.get("imports_by_language") or {}
    if seen == 0 and internal == 0 and filtered == 0:
        return []
    lines = [
        f"{indent}imports_seen: {seen}",
        f"{indent}imports_internal: {internal}",
        f"{indent}imports_filtered_not_internal: {filtered}",
    ]
    for language in sorted(by_language):
        item = by_language.get(language) or {}
        lines.append(
            f"{indent}{language}: "
            f"seen={int(item.get('imports_seen') or 0)}, "
            f"internal={int(item.get('imports_internal') or 0)}, "
            f"filtered_not_internal={int(item.get('imports_filtered_not_internal') or 0)}"
        )
    return lines


def _render_scope_count_lines(
    pair_payload: dict[str, dict[str, object]] | None,
    edge_payload: dict[str, dict[str, object]] | None,
    *,
    indent: str,
) -> list[str]:
    if not pair_payload and not edge_payload:
        return []
    lines: list[str] = []
    for scope_key in ("non_tests", "tests"):
        pair_scope = pair_payload.get(scope_key) if pair_payload else None
        edge_scope = edge_payload.get(scope_key) if edge_payload else None
        pair_count = int((pair_scope or {}).get("count") or 0)
        edge_count = int((edge_scope or {}).get("count") or 0)
        lines.append(f"{indent}{scope_key}: pairs={pair_count}, edges={edge_count}")
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
