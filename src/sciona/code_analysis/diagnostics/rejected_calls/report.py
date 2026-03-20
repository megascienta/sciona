# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Filesystem helpers for optional rejected-call diagnostic runs."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil

from .models import DIAGNOSTIC_BUCKET_KEYS

PUBLIC_DIAGNOSTIC_BUCKET_KEYS = (
    "outside_static_contract",
    "insufficient_static_evidence",
    "structural_mismatch",
    "unclassified",
)

_PUBLIC_DIAGNOSTIC_BUCKET_MAP = {
    "no_in_repo_candidate": "unclassified",
    "insufficient_static_evidence": "insufficient_static_evidence",
    "outside_in_repo_scope": "outside_static_contract",
    "invalid_observation_shape": "structural_mismatch",
    "external_dependency_shape": "outside_static_contract",
    "builtin_or_standard_shape": "outside_static_contract",
    "dynamic_or_indirect_shape": "outside_static_contract",
    "unindexed_symbol_shape": "insufficient_static_evidence",
    "parser_extraction_mismatch": "structural_mismatch",
    "no_clear_in_repo_target": "unclassified",
}


def build_status_output_path(repo_root: Path) -> Path:
    return repo_root / f"{repo_root.name}_build_status.json"


def rejected_calls_verbose_output_path(repo_root: Path) -> Path:
    return repo_root / f"{repo_root.name}_not_accepted_verbose.json"


def enrich_report(
    report: dict[str, object],
    diagnostic_payload: dict[str, object] | None,
) -> dict[str, object]:
    if not diagnostic_payload:
        return dict(report)
    enriched = dict(report)
    labels = dict(enriched.get("labels") or {})
    sections = dict(labels.get("sections") or {})
    sections["not_accepted_callsites"] = "Not Accepted Callsites"
    labels["sections"] = sections
    fields = dict(labels.get("fields") or {})
    fields.update(
        {
            "outside_static_contract": "Outside Static Contract",
            "insufficient_static_evidence": "Insufficient Static Evidence",
            "structural_mismatch": "Structural Mismatch",
            "unclassified": "Unclassified",
            "build_phase_timings": "Build Phase Timing",
        }
    )
    labels["fields"] = fields
    enriched["labels"] = labels
    _replace_not_accepted_callsites(
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
        bucket = str(item.get("bucket") or "no_clear_in_repo_target")
        bucket_entry = by_bucket.setdefault(
            bucket,
            {"count": 0, "callsites": [], "reasons": {}, "signals": {}},
        )
        bucket_entry["count"] = int(bucket_entry.get("count", 0)) + 1
        cast_callsites = bucket_entry.setdefault("callsites", [])
        if isinstance(cast_callsites, list):
            cast_callsites.append(item)
        bucket_reasons = bucket_entry.setdefault("reasons", {})
        if isinstance(bucket_reasons, dict):
            for reason in item.get("reasons") or []:
                bucket_reasons[str(reason)] = int(bucket_reasons.get(str(reason), 0)) + 1
        bucket_signals = bucket_entry.setdefault("signals", {})
        if isinstance(bucket_signals, dict):
            for signal in item.get("signals") or []:
                bucket_signals[str(signal)] = int(bucket_signals.get(str(signal), 0)) + 1
        file_path = str(item.get("file_path") or "")
        if not file_path:
            continue
        file_entry = by_file.setdefault(
            file_path,
            {"file_path": file_path, "count": 0, "buckets": {}, "reasons": {}, "signals": {}},
        )
        file_entry["count"] = int(file_entry.get("count", 0)) + 1
        buckets = file_entry.setdefault("buckets", {})
        if isinstance(buckets, dict):
            buckets[bucket] = int(buckets.get(bucket, 0)) + 1
        file_reasons = file_entry.setdefault("reasons", {})
        if isinstance(file_reasons, dict):
            for reason in item.get("reasons") or []:
                file_reasons[str(reason)] = int(file_reasons.get(str(reason), 0)) + 1
        file_signals = file_entry.setdefault("signals", {})
        if isinstance(file_signals, dict):
            for signal in item.get("signals") or []:
                file_signals[str(signal)] = int(file_signals.get(str(signal), 0)) + 1
    problematic_files = sorted(
        by_file.values(),
        key=lambda row: (-int(row.get("count", 0)), str(row.get("file_path") or "")),
    )
    return {
        "buckets": {
            bucket: {
                "count": int((payload or {}).get("count", 0)),
                "reasons": dict((payload or {}).get("reasons") or {}),
                "signals": dict((payload or {}).get("signals") or {}),
                "callsites": list((payload or {}).get("callsites") or []),
            }
            for bucket, payload in sorted(by_bucket.items())
        },
        "problematic_callsites": observations,
        "problematic_files": problematic_files,
    }


def build_persisted_drop_verbose_payload(
    diagnostics_payload: dict[str, object] | None,
) -> dict[str, object]:
    observations = list((diagnostics_payload or {}).get("persisted_drop_observations") or [])
    by_bucket: dict[str, dict[str, object]] = {}
    by_file: dict[str, dict[str, object]] = {}
    for item in observations:
        if not isinstance(item, dict):
            continue
        bucket = _persisted_drop_bucket(item)
        bucket_entry = by_bucket.setdefault(
            bucket,
            {"count": 0, "callsites": [], "reasons": {}, "signals": {}},
        )
        bucket_entry["count"] = int(bucket_entry.get("count", 0)) + 1
        cast_callsites = bucket_entry.setdefault("callsites", [])
        if isinstance(cast_callsites, list):
            enriched_item = dict(item)
            enriched_item["bucket"] = bucket
            cast_callsites.append(enriched_item)
        bucket_reasons = bucket_entry.setdefault("reasons", {})
        if isinstance(bucket_reasons, dict):
            reason = str(item.get("drop_reason") or "unclassified")
            bucket_reasons[reason] = int(bucket_reasons.get(reason, 0)) + 1
        bucket_signals = bucket_entry.setdefault("signals", {})
        if isinstance(bucket_signals, dict):
            for signal in _persisted_drop_signals(item):
                bucket_signals[signal] = int(bucket_signals.get(signal, 0)) + 1
        file_path = str(item.get("file_path") or "")
        if not file_path:
            continue
        file_entry = by_file.setdefault(
            file_path,
            {"file_path": file_path, "count": 0, "buckets": {}, "reasons": {}, "signals": {}},
        )
        file_entry["count"] = int(file_entry.get("count", 0)) + 1
        buckets = file_entry.setdefault("buckets", {})
        if isinstance(buckets, dict):
            buckets[bucket] = int(buckets.get(bucket, 0)) + 1
        file_reasons = file_entry.setdefault("reasons", {})
        if isinstance(file_reasons, dict):
            reason = str(item.get("drop_reason") or "unclassified")
            file_reasons[reason] = int(file_reasons.get(reason, 0)) + 1
        file_signals = file_entry.setdefault("signals", {})
        if isinstance(file_signals, dict):
            for signal in _persisted_drop_signals(item):
                file_signals[signal] = int(file_signals.get(signal, 0)) + 1
    problematic_files = sorted(
        by_file.values(),
        key=lambda row: (-int(row.get("count", 0)), str(row.get("file_path") or "")),
    )
    problematic_callsites = []
    for bucket in sorted(by_bucket):
        payload = by_bucket[bucket]
        problematic_callsites.extend(list((payload or {}).get("callsites") or []))
    return {
        "buckets": {
            bucket: {
                "count": int((payload or {}).get("count", 0)),
                "reasons": dict((payload or {}).get("reasons") or {}),
                "signals": dict((payload or {}).get("signals") or {}),
                "callsites": list((payload or {}).get("callsites") or []),
            }
            for bucket, payload in sorted(by_bucket.items())
        },
        "problematic_callsites": problematic_callsites,
        "problematic_files": problematic_files,
    }


def build_rejected_calls_verbose_payload(
    diagnostic_payload: dict[str, object] | None,
    persisted_drop_payload: dict[str, object] | None,
) -> dict[str, object]:
    by_bucket: dict[str, dict[str, object]] = {}
    by_file: dict[str, dict[str, object]] = {}
    problematic_callsites: list[dict[str, object]] = []

    for item in list((diagnostic_payload or {}).get("observations") or []):
        if not isinstance(item, dict):
            continue
        public_bucket = _PUBLIC_DIAGNOSTIC_BUCKET_MAP.get(
            str(item.get("bucket") or "no_clear_in_repo_target"),
            "unclassified",
        )
        enriched = dict(item)
        enriched["public_bucket"] = public_bucket
        enriched["source_bucket"] = str(
            item.get("bucket") or "no_clear_in_repo_target"
        )
        _accumulate_rejected_callsite(
            by_bucket,
            by_file,
            problematic_callsites,
            enriched,
            public_bucket=public_bucket,
            reasons=item.get("reasons") or [],
            signals=item.get("signals") or [],
        )

    for item in list((persisted_drop_payload or {}).get("persisted_drop_observations") or []):
        if not isinstance(item, dict):
            continue
        source_bucket = _persisted_drop_bucket(item)
        public_bucket = _public_bucket_for_persisted_drop(item, source_bucket=source_bucket)
        signals = _persisted_drop_signals(item)
        reason = str(item.get("drop_reason") or "unclassified")
        enriched = dict(item)
        enriched["public_bucket"] = public_bucket
        enriched["source_bucket"] = source_bucket
        enriched["signals"] = list(signals)
        _accumulate_rejected_callsite(
            by_bucket,
            by_file,
            problematic_callsites,
            enriched,
            public_bucket=public_bucket,
            reasons=(reason,),
            signals=signals,
        )

    problematic_files = sorted(
        by_file.values(),
        key=lambda row: (-int(row.get("count", 0)), str(row.get("file_path") or "")),
    )
    return {
        "buckets": {
            bucket: {
                "count": int((payload or {}).get("count", 0)),
                "reasons": dict((payload or {}).get("reasons") or {}),
                "signals": dict((payload or {}).get("signals") or {}),
                "callsites": list((payload or {}).get("callsites") or []),
            }
            for bucket, payload in sorted(by_bucket.items())
        },
        "problematic_callsites": problematic_callsites,
        "problematic_files": problematic_files,
    }


def empty_diagnostic_buckets() -> dict[str, int]:
    return {key: 0 for key in DIAGNOSTIC_BUCKET_KEYS}


def _replace_not_accepted_callsites(
    report: dict[str, object],
    *,
    totals: object,
    by_language: object,
    by_scope: object,
) -> None:
    totals_payload = report.get("totals")
    if isinstance(totals_payload, dict):
        updated_totals = dict(totals_payload)
        updated_totals["not_accepted_callsites"] = _merge_non_candidate_buckets(
            dict(
                updated_totals.get("not_accepted_callsites")
                or updated_totals.get("not_accepted_calls")
                or {}
            ),
            totals if isinstance(totals, dict) else {},
        )
        updated_totals.pop("not_accepted_calls", None)
        report["totals"] = updated_totals
    if isinstance(report.get("languages"), dict):
        language_buckets = by_language if isinstance(by_language, dict) else {}
        updated_languages = {}
        for language_key, language_value in (report.get("languages") or {}).items():
            if not isinstance(language_value, dict):
                updated_languages[language_key] = language_value
                continue
            updated = dict(language_value)
            updated["not_accepted_callsites"] = _merge_non_candidate_buckets(
                dict(
                    updated.get("not_accepted_callsites")
                    or updated.get("not_accepted_calls")
                    or {}
                ),
                language_buckets.get(language_key)
                if isinstance(language_buckets.get(language_key), dict)
                else {},
            )
            updated.pop("not_accepted_calls", None)
            updated_languages[language_key] = updated
        report["languages"] = updated_languages
    if isinstance(report.get("scopes"), dict):
        scope_buckets = by_scope if isinstance(by_scope, dict) else {}
        updated_scopes = {}
        for scope_key, scope_value in (report.get("scopes") or {}).items():
            if not isinstance(scope_value, dict):
                updated_scopes[scope_key] = scope_value
                continue
            updated = dict(scope_value)
            updated["not_accepted_callsites"] = _merge_non_candidate_buckets(
                dict(
                    updated.get("not_accepted_callsites")
                    or updated.get("not_accepted_calls")
                    or {}
                ),
                scope_buckets.get(scope_key)
                if isinstance(scope_buckets.get(scope_key), dict)
                else {},
            )
            updated.pop("not_accepted_calls", None)
            updated_scopes[scope_key] = updated
        report["scopes"] = updated_scopes


def _merge_non_candidate_buckets(
    canonical_buckets: dict[str, int],
    diagnostic_buckets: dict[str, int],
) -> dict[str, int]:
    payload = {key: 0 for key in PUBLIC_DIAGNOSTIC_BUCKET_KEYS}
    for source in (canonical_buckets, diagnostic_buckets):
        for key, value in source.items():
            public_key = _PUBLIC_DIAGNOSTIC_BUCKET_MAP.get(str(key), "unclassified")
            payload[public_key] = int(payload.get(public_key, 0)) + int(value or 0)
    return payload


@contextmanager
def diagnostic_workspace(sciona_dir: Path):
    workspace = sciona_dir / ".diagnostic_rejected_calls"
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _persisted_drop_bucket(item: dict[str, object]) -> str:
    identifier = str(item.get("identifier") or "")
    file_path = str(item.get("file_path") or "")
    drop_reason = str(item.get("drop_reason") or "")
    candidate_count = int(item.get("candidate_count") or 0)
    terminal = identifier.rsplit(".", 1)[-1]
    if _is_fixture_or_generated_path(file_path):
        return "fixture_or_generated_shape"
    if any(token in identifier for token in (".then", ".catch")):
        return "fluent_or_promise_chain_shape"
    if any(token in identifier for token in (".finally", ".in(")):
        return "dynamic_member_terminal_shape"
    if identifier.endswith(".emit") or ".emit" in identifier:
        return "dynamic_member_terminal_shape"
    if terminal in {
        "filter",
        "find",
        "flatMap",
        "forEach",
        "includes",
        "map",
        "reduce",
        "slice",
        "some",
        "has",
        "keys",
        "values",
        "entries",
    }:
        return "dynamic_member_terminal_shape"
    if ".server." in identifier or ".notifications." in identifier or ".tools." in identifier:
        return "namespace_or_module_object_miss_shape"
    if (
        drop_reason == "unique_without_provenance"
        and candidate_count == 1
        and ".index." in identifier
    ):
        return "runtime_composed_surface_shape"
    if drop_reason == "no_candidates" or candidate_count <= 0:
        return "no_in_repo_callable_target"
    return "unclassified_persisted_drop"


def _public_bucket_for_persisted_drop(
    item: dict[str, object],
    *,
    source_bucket: str,
) -> str:
    if source_bucket in {
        "fixture_or_generated_shape",
        "fluent_or_promise_chain_shape",
        "dynamic_member_terminal_shape",
        "runtime_composed_surface_shape",
    }:
        return "outside_static_contract"
    if source_bucket in {
        "namespace_or_module_object_miss_shape",
        "no_in_repo_callable_target",
    }:
        return "insufficient_static_evidence"
    drop_reason = str(item.get("drop_reason") or "")
    if drop_reason in {"invalid_observation_shape"}:
        return "structural_mismatch"
    if drop_reason:
        return "insufficient_static_evidence"
    return "unclassified"


def _persisted_drop_signals(item: dict[str, object]) -> tuple[str, ...]:
    identifier = str(item.get("identifier") or "")
    file_path = str(item.get("file_path") or "")
    signals: list[str] = []
    if "." in identifier:
        signals.append(f"identifier_depth:{len([part for part in identifier.split('.') if part])}")
    if any(token in identifier for token in (".then", ".catch")):
        signals.append("promise_chain_terminal")
    if ".emit" in identifier:
        signals.append("event_emitter_terminal")
    if ".in(" in identifier:
        signals.append("dynamic_member_call_chain")
    if ".tools." in identifier:
        signals.append("namespace_subobject")
    if ".server." in identifier:
        signals.append("server_namespace")
    if ".index." in identifier:
        signals.append("index_proxy_surface")
    if _is_fixture_or_generated_path(file_path):
        signals.append("fixture_or_generated_path")
    return tuple(signals)


def _is_fixture_or_generated_path(file_path: str) -> bool:
    parts = [segment.lower() for segment in file_path.replace("\\", "/").split("/") if segment]
    if not parts:
        return False
    markers = {
        "__fixtures__",
        "fixture",
        "fixtures",
        "_expected",
        "expected",
        "generated",
        "__generated__",
        "snapshots",
        "__snapshots__",
    }
    return any(part in markers for part in parts)


def _accumulate_rejected_callsite(
    by_bucket: dict[str, dict[str, object]],
    by_file: dict[str, dict[str, object]],
    problematic_callsites: list[dict[str, object]],
    item: dict[str, object],
    *,
    public_bucket: str,
    reasons: object,
    signals: object,
) -> None:
    problematic_callsites.append(item)

    bucket_entry = by_bucket.setdefault(
        public_bucket,
        {
            "count": 0,
            "callsites": [],
            "reasons": {},
            "signals": {},
        },
    )
    bucket_entry["count"] = int(bucket_entry.get("count", 0)) + 1
    cast_callsites = bucket_entry.setdefault("callsites", [])
    if isinstance(cast_callsites, list):
        cast_callsites.append(item)
    bucket_reasons = bucket_entry.setdefault("reasons", {})
    if isinstance(bucket_reasons, dict):
        for reason in reasons if isinstance(reasons, (list, tuple)) else ():
            bucket_reasons[str(reason)] = int(bucket_reasons.get(str(reason), 0)) + 1
    bucket_signals = bucket_entry.setdefault("signals", {})
    if isinstance(bucket_signals, dict):
        for signal in signals if isinstance(signals, (list, tuple)) else ():
            bucket_signals[str(signal)] = int(bucket_signals.get(str(signal), 0)) + 1

    file_path = str(item.get("file_path") or "")
    if not file_path:
        return
    file_entry = by_file.setdefault(
        file_path,
        {
            "file_path": file_path,
            "count": 0,
            "buckets": {},
            "reasons": {},
            "signals": {},
        },
    )
    file_entry["count"] = int(file_entry.get("count", 0)) + 1
    file_buckets = file_entry.setdefault("buckets", {})
    if isinstance(file_buckets, dict):
        file_buckets[public_bucket] = int(file_buckets.get(public_bucket, 0)) + 1
    file_reasons = file_entry.setdefault("reasons", {})
    if isinstance(file_reasons, dict):
        for reason in reasons if isinstance(reasons, (list, tuple)) else ():
            file_reasons[str(reason)] = int(file_reasons.get(str(reason), 0)) + 1
    file_signals = file_entry.setdefault("signals", {})
    if isinstance(file_signals, dict):
        for signal in signals if isinstance(signals, (list, tuple)) else ():
            file_signals[str(signal)] = int(file_signals.get(str(signal), 0)) + 1
