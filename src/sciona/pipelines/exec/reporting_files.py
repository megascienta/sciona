# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""File-discovery and density helpers for snapshot reporting."""

from __future__ import annotations

from collections import defaultdict

from ...code_analysis.tools import walker as file_walker
from ...runtime import config as runtime_config
from ...runtime import git as git_ops
from .reporting_callsites import top_items


def structural_density_payload(
    *,
    files: int,
    nodes: int,
    eligible_callsites: int,
    file_node_distribution: list[tuple[str, int]],
    discovered_files: int | None,
) -> dict[str, object]:
    nodes_per_file = (nodes / files) if files > 0 else None
    eligible_callsites_per_file = (eligible_callsites / files) if files > 0 else None
    low_node_files = [(path, count) for path, count in file_node_distribution if count <= 1]
    low_node_dir_counts: dict[str, int] = {}
    for file_path, _count in low_node_files:
        bucket = directory_bucket(file_path)
        low_node_dir_counts[bucket] = low_node_dir_counts.get(bucket, 0) + 1
    top_low_node_dirs = top_items(low_node_dir_counts, limit=5)
    low_node_ratio = (len(low_node_files) / files) if files > 0 else None
    inferred_zero_node_files = (
        max(int(discovered_files or 0) - files, 0)
        if discovered_files is not None
        else None
    )
    inferred_zero_node_ratio = (
        (inferred_zero_node_files / int(discovered_files))
        if discovered_files is not None and int(discovered_files) > 0 and inferred_zero_node_files is not None
        else None
    )
    inflation_warning = bool(
        files >= 200 and low_node_ratio is not None and low_node_ratio >= 0.60
    )
    if (
        not inflation_warning
        and discovered_files is not None
        and int(discovered_files) >= 200
        and inferred_zero_node_ratio is not None
        and inferred_zero_node_ratio >= 0.40
    ):
        inflation_warning = True
    warnings: list[str] = []
    if low_node_ratio is not None and low_node_ratio >= 0.60:
        warnings.append("low_node_file_ratio_high")
    if inferred_zero_node_ratio is not None and inferred_zero_node_ratio >= 0.40:
        warnings.append("inferred_zero_node_ratio_high")
    return {
        "files": files,
        "discovered_files": discovered_files,
        "nodes": nodes,
        "eligible_callsites": eligible_callsites,
        "nodes_per_file": nodes_per_file,
        "eligible_callsites_per_file": eligible_callsites_per_file,
        "low_node_files_leq_1": len(low_node_files),
        "low_node_file_ratio": low_node_ratio,
        "inferred_zero_node_files": inferred_zero_node_files,
        "inferred_zero_node_ratio": inferred_zero_node_ratio,
        "top_low_node_dirs": top_low_node_dirs,
        "inflation_warning": inflation_warning,
        "warnings": warnings,
        "zero_node_files_observed": 0,
        "zero_node_files_note": "Not observable from indexed files; files without nodes are not materialized in node_instances.",
    }


def directory_bucket(file_path: str) -> str:
    normalized = file_path.replace("\\", "/").strip("/")
    if not normalized:
        return "."
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return "."
    if len(parts) == 1:
        return parts[0]
    return "/".join(parts[:2])


def discovered_files_by_language(repo_root) -> dict[str, int]:
    try:
        config = runtime_config.load_runtime_config(repo_root)
        tracked = git_ops.tracked_paths(repo_root)
        ignored = git_ops.ignored_tracked_paths(repo_root)
        records = file_walker.collect_files(
            repo_root,
            config.languages,
            discovery=config.discovery,
            tracked_paths=tracked,
            ignored_paths=ignored,
        )
    except Exception:
        return {}
    counts: dict[str, int] = defaultdict(int)
    for record in records:
        counts[str(record.language)] += 1
    return dict(counts)
