# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Filesystem helpers for optional pre-persist diagnostic runs."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil

from .models import DIAGNOSTIC_BUCKET_KEYS


def build_status_output_path(repo_root: Path) -> Path:
    return repo_root / f"{repo_root.name}_build_status.json"


def pre_persist_verbose_output_path(repo_root: Path) -> Path:
    return repo_root / f"{repo_root.name}_pre_persist_verbose.json"


def enrich_report(
    report: dict[str, object],
    diagnostic_payload: dict[str, object] | None,
) -> dict[str, object]:
    if not diagnostic_payload:
        return dict(report)
    enriched = dict(report)
    labels = dict(enriched.get("labels") or {})
    fields = dict(labels.get("fields") or {})
    fields.update(
        {
            "likely_external_dependency": "Likely External Dependency",
            "likely_standard_library_or_builtin": "Likely Standard Library Or Builtin",
            "likely_dynamic_dispatch_or_indirect": "Likely Dynamic Dispatch Or Indirect",
            "likely_unindexed_symbol": "Likely Unindexed Symbol",
            "likely_parser_extraction_gap": "Likely Parser Extraction Gap",
            "unclassified_no_in_repo_candidate": "Unclassified No In-Repo Candidate",
        }
    )
    labels["fields"] = fields
    enriched["labels"] = labels
    _replace_pre_persist_filters(
        enriched,
        totals=diagnostic_payload.get("totals"),
        by_language=diagnostic_payload.get("by_language"),
        by_scope=diagnostic_payload.get("by_scope"),
    )
    return enriched


def build_verbose_payload(
    diagnostic_payload: dict[str, object] | None,
) -> dict[str, object]:
    observations = list((diagnostic_payload or {}).get("observations") or [])
    by_bucket: dict[str, dict[str, object]] = {}
    by_file: dict[str, dict[str, object]] = {}
    for item in observations:
        if not isinstance(item, dict):
            continue
        bucket = str(item.get("bucket") or "unclassified_no_in_repo_candidate")
        bucket_entry = by_bucket.setdefault(
            bucket,
            {"count": 0, "callsites": []},
        )
        bucket_entry["count"] = int(bucket_entry.get("count", 0)) + 1
        cast_callsites = bucket_entry.setdefault("callsites", [])
        if isinstance(cast_callsites, list):
            cast_callsites.append(item)
        file_path = str(item.get("file_path") or "")
        if not file_path:
            continue
        file_entry = by_file.setdefault(
            file_path,
            {"file_path": file_path, "count": 0, "buckets": {}},
        )
        file_entry["count"] = int(file_entry.get("count", 0)) + 1
        buckets = file_entry.setdefault("buckets", {})
        if isinstance(buckets, dict):
            buckets[bucket] = int(buckets.get(bucket, 0)) + 1
    problematic_files = sorted(
        by_file.values(),
        key=lambda row: (-int(row.get("count", 0)), str(row.get("file_path") or "")),
    )
    return {
        "buckets": {
            bucket: {
                "count": int((payload or {}).get("count", 0)),
                "callsites": list((payload or {}).get("callsites") or []),
            }
            for bucket, payload in sorted(by_bucket.items())
        },
        "problematic_callsites": observations,
        "problematic_files": problematic_files,
    }


def empty_diagnostic_buckets() -> dict[str, int]:
    return {key: 0 for key in DIAGNOSTIC_BUCKET_KEYS}


def _replace_pre_persist_filters(
    report: dict[str, object],
    *,
    totals: object,
    by_language: object,
    by_scope: object,
) -> None:
    totals_payload = report.get("totals")
    if isinstance(totals_payload, dict):
        updated_totals = dict(totals_payload)
        updated_totals["pre_persist_filter"] = _merge_non_candidate_buckets(
            dict(updated_totals.get("pre_persist_filter") or {}),
            totals if isinstance(totals, dict) else {},
        )
        report["totals"] = updated_totals
    if isinstance(report.get("languages"), list):
        language_buckets = by_language if isinstance(by_language, dict) else {}
        updated_languages = []
        for item in report.get("languages") or []:
            if not isinstance(item, dict):
                updated_languages.append(item)
                continue
            updated = dict(item)
            language = str(updated.get("language") or "")
            updated["pre_persist_filter"] = _merge_non_candidate_buckets(
                dict(updated.get("pre_persist_filter") or {}),
                language_buckets.get(language)
                if isinstance(language_buckets.get(language), dict)
                else {},
            )
            updated_languages.append(updated)
        report["languages"] = updated_languages
    if isinstance(report.get("scopes"), dict):
        scope_buckets = by_scope if isinstance(by_scope, dict) else {}
        updated_scopes = {}
        for scope_key, scope_value in (report.get("scopes") or {}).items():
            if not isinstance(scope_value, dict):
                updated_scopes[scope_key] = scope_value
                continue
            updated = dict(scope_value)
            updated["pre_persist_filter"] = _merge_non_candidate_buckets(
                dict(updated.get("pre_persist_filter") or {}),
                scope_buckets.get(scope_key)
                if isinstance(scope_buckets.get(scope_key), dict)
                else {},
            )
            updated_scopes[scope_key] = updated
        report["scopes"] = updated_scopes


def _merge_non_candidate_buckets(
    canonical_buckets: dict[str, int],
    diagnostic_buckets: dict[str, int],
) -> dict[str, int]:
    payload = empty_diagnostic_buckets()
    payload["accepted_outside_in_repo"] = int(
        canonical_buckets.get("accepted_outside_in_repo", 0)
    )
    payload["invalid_observation_shape"] = int(
        canonical_buckets.get("invalid_observation_shape", 0)
    )
    for key, value in diagnostic_buckets.items():
        if key in payload:
            payload[key] = int(value or 0)
    return payload


@contextmanager
def diagnostic_workspace(sciona_dir: Path):
    workspace = sciona_dir / ".diagnostic_pre_persist"
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
