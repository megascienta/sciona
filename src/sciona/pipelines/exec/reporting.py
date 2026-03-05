# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""DB-backed snapshot reporting for CLI summaries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import sqlite3

from ..domain.repository import RepoState
from ...data_storage.connections import artifact_readonly, core_readonly
from ...data_storage.core_db import read_ops as core_read
from ...data_storage.artifact_db import read_reporting as artifact_reporting


@dataclass(frozen=True)
class LanguageMetrics:
    language: str
    files: int = 0
    nodes: int = 0
    edges: int = 0
    call_sites_eligible: int | None = None
    call_sites_accepted: int | None = None
    call_sites_dropped: int | None = None
    drop_reasons: dict[str, int] = field(default_factory=dict)
    drop_classification: dict[str, int] = field(default_factory=dict)
    drop_classification_by_scope: dict[str, dict[str, int]] = field(default_factory=dict)
    drop_reason_examples: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    accepted_examples: list[dict[str, object]] = field(default_factory=list)

    def to_payload(self, *, include_failure_reasons: bool) -> dict[str, object]:
        payload: dict[str, object] = {
            "language": self.language,
            "files": self.files,
            "nodes": self.nodes,
            "edges": self.edges,
        }
        payload["call_sites"] = _call_sites_payload(
            self.call_sites_eligible,
            self.call_sites_accepted,
            self.call_sites_dropped,
        )
        if include_failure_reasons and self.drop_reasons:
            payload["drop_reasons"] = dict(sorted(self.drop_reasons.items()))
        if include_failure_reasons and self.drop_classification:
            payload["drop_classification"] = dict(sorted(self.drop_classification.items()))
        if include_failure_reasons and self.drop_classification_by_scope:
            payload["drop_classification_by_scope"] = {
                scope: dict(sorted(counts.items()))
                for scope, counts in sorted(self.drop_classification_by_scope.items())
            }
        if include_failure_reasons and self.drop_reason_examples:
            payload["drop_reason_examples"] = {
                reason: examples
                for reason, examples in sorted(self.drop_reason_examples.items())
            }
        if include_failure_reasons and self.accepted_examples:
            payload["accepted_examples"] = list(self.accepted_examples)
        return payload


def snapshot_report(
    repo_state: RepoState,
    *,
    snapshot_id: str,
    include_failure_reasons: bool = False,
) -> dict[str, object] | None:
    language_metrics: dict[str, LanguageMetrics] = {}
    caller_language: dict[str, str] = {}
    caller_metadata: dict[str, dict[str, object]] = {}
    callable_identifiers_by_language: dict[str, set[str]] = {}
    file_node_distribution_by_language: dict[str, list[tuple[str, int]]] = {}
    created_at: str | None = None

    with core_readonly(repo_state.db_path, repo_root=repo_state.repo_root) as conn:
        created_at = core_read.snapshot_created_at(conn, snapshot_id)
        if created_at is None:
            return None
        files_and_nodes = core_read.language_file_node_counts(conn, snapshot_id)
        for item in files_and_nodes:
            language = str(item["language"])
            language_metrics[language] = LanguageMetrics(
                language=language,
                files=int(item["file_count"] or 0),
                nodes=int(item["node_count"] or 0),
            )
        edge_counts = core_read.language_edge_counts(conn, snapshot_id)
        for item in edge_counts:
            language = str(item["language"])
            current = language_metrics.get(language, LanguageMetrics(language=language))
            language_metrics[language] = LanguageMetrics(
                language=language,
                files=current.files,
                nodes=current.nodes,
                edges=int(item["edge_count"] or 0),
                call_sites_eligible=current.call_sites_eligible,
                call_sites_accepted=current.call_sites_accepted,
                call_sites_dropped=current.call_sites_dropped,
                drop_reasons=current.drop_reasons,
                drop_classification=current.drop_classification,
                drop_classification_by_scope=current.drop_classification_by_scope,
            )
        caller_metadata = core_read.caller_node_metadata_map(conn, snapshot_id)
        caller_language = {
            structural_id: str(meta["language"])
            for structural_id, meta in caller_metadata.items()
        }
        callable_identifiers_by_language = _build_callable_identifier_index(caller_metadata)
        file_node_distribution = core_read.language_file_node_distribution(conn, snapshot_id)
        for item in file_node_distribution:
            language = str(item.get("language") or "")
            file_path = str(item.get("file_path") or "")
            node_count = int(item.get("node_count") or 0)
            if not language or not file_path:
                continue
            file_node_distribution_by_language.setdefault(language, []).append(
                (file_path, node_count)
            )

    artifact_available = False
    call_site_reasons: dict[str, dict[str, int]] = defaultdict(dict)
    drop_classification: dict[str, dict[str, int]] = defaultdict(dict)
    drop_classification_by_scope: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: {"non_tests": {}, "tests": {}}
    )
    call_site_reason_examples: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(dict)
    call_site_accept_examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    failure_hotspots_callers: dict[str, dict[str, int]] = defaultdict(dict)
    failure_hotspots_files: dict[str, dict[str, int]] = defaultdict(dict)
    call_site_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"eligible": 0, "accepted": 0, "dropped": 0}
    )
    call_site_scope_totals: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: {
            "non_tests": {"eligible": 0, "accepted": 0, "dropped": 0},
            "tests": {"eligible": 0, "accepted": 0, "dropped": 0},
        }
    )
    try:
        with artifact_readonly(
            repo_state.artifact_db_path, repo_root=repo_state.repo_root
        ) as conn:
            artifact_available = True
            call_sites = artifact_reporting.call_site_caller_status_counts(
                conn,
                snapshot_id=snapshot_id,
            )
            for item in call_sites:
                language = caller_language.get(str(item["caller_id"]))
                if not language:
                    continue
                count = int(item["site_count"] or 0)
                caller_info = caller_metadata.get(str(item["caller_id"])) or {}
                caller_file_path = str(caller_info.get("file_path") or "")
                scope_key = _scope_bucket(caller_file_path)
                call_site_totals[language]["eligible"] += count
                call_site_scope_totals[language][scope_key]["eligible"] += count
                status = str(item["resolution_status"])
                if status == "accepted":
                    call_site_totals[language]["accepted"] += count
                    call_site_scope_totals[language][scope_key]["accepted"] += count
                else:
                    call_site_totals[language]["dropped"] += count
                    call_site_scope_totals[language][scope_key]["dropped"] += count
                    reason = str(item["drop_reason"] or "unknown")
                    call_site_reasons[language][reason] = (
                        call_site_reasons[language].get(reason, 0) + count
                    )
            dropped_identifiers = artifact_reporting.call_site_drop_identifier_counts(
                conn,
                snapshot_id=snapshot_id,
            )
            for item in dropped_identifiers:
                caller_id = str(item["caller_id"])
                language = caller_language.get(caller_id)
                if not language:
                    continue
                caller_info = caller_metadata.get(caller_id, {})
                scope_key = _scope_bucket(str(caller_info.get("file_path") or ""))
                bucket = _drop_classification_bucket(
                    identifier=str(item.get("identifier") or ""),
                    drop_reason=str(item.get("drop_reason") or ""),
                    candidate_count=int(item.get("candidate_count") or 0),
                    callee_kind=str(item.get("callee_kind") or ""),
                    known_callable_identifiers=callable_identifiers_by_language.get(
                        language, set()
                    ),
                )
                if not bucket:
                    continue
                count = int(item.get("site_count") or 0)
                drop_classification[language][bucket] = (
                    drop_classification[language].get(bucket, 0) + count
                )
                scoped = drop_classification_by_scope[language][scope_key]
                scoped[bucket] = scoped.get(bucket, 0) + count
            if include_failure_reasons:
                dropped_sites = artifact_reporting.call_site_drop_debug_counts(
                    conn,
                    snapshot_id=snapshot_id,
                )
                for item in dropped_sites:
                    caller_id = str(item["caller_id"])
                    language = caller_language.get(caller_id)
                    if not language:
                        continue
                    caller_info = caller_metadata.get(caller_id, {})
                    caller_qname = str(
                        caller_info.get("qualified_name") or item.get("caller_qname") or ""
                    )
                    caller_file_path = str(caller_info.get("file_path") or "")
                    count = int(item.get("site_count") or 0)
                    if caller_qname:
                        failure_hotspots_callers[language][caller_qname] = (
                            failure_hotspots_callers[language].get(caller_qname, 0) + count
                        )
                    if caller_file_path:
                        failure_hotspots_files[language][caller_file_path] = (
                            failure_hotspots_files[language].get(caller_file_path, 0) + count
                        )
                    reason = str(item["drop_reason"] or "unknown")
                    by_reason = call_site_reason_examples[language].setdefault(reason, [])
                    if len(by_reason) >= 8:
                        continue
                    by_reason.append(
                        {
                            "caller_id": caller_id,
                            "caller_qname": caller_qname,
                            "caller_file_path": caller_file_path or None,
                            "caller_node_type": caller_info.get("node_type"),
                            "caller_span": [
                                caller_info.get("start_line"),
                                caller_info.get("end_line"),
                            ],
                            "identifier": str(item.get("identifier") or ""),
                            "candidate_count": int(item.get("candidate_count") or 0),
                            "in_scope_candidate_count": item.get(
                                "in_scope_candidate_count"
                            ),
                            "candidate_module_hints": item.get("candidate_module_hints"),
                            "callee_kind": str(item.get("callee_kind") or ""),
                            "count": count,
                        }
                    )
                accepted_sites = artifact_reporting.call_site_accept_debug_counts(
                    conn,
                    snapshot_id=snapshot_id,
                )
                for item in accepted_sites:
                    caller_id = str(item["caller_id"])
                    language = caller_language.get(caller_id)
                    if not language:
                        continue
                    examples = call_site_accept_examples[language]
                    if len(examples) >= 8:
                        continue
                    caller_info = caller_metadata.get(caller_id, {})
                    examples.append(
                        {
                            "caller_id": caller_id,
                            "caller_qname": str(
                                caller_info.get("qualified_name")
                                or item.get("caller_qname")
                                or ""
                            ),
                            "caller_file_path": str(caller_info.get("file_path") or "") or None,
                            "caller_node_type": caller_info.get("node_type"),
                            "caller_span": [
                                caller_info.get("start_line"),
                                caller_info.get("end_line"),
                            ],
                            "identifier": str(item.get("identifier") or ""),
                            "accepted_callee_id": str(item.get("accepted_callee_id") or ""),
                            "provenance": str(item.get("provenance") or ""),
                            "candidate_count": int(item.get("candidate_count") or 0),
                            "callee_kind": str(item.get("callee_kind") or ""),
                            "count": int(item.get("site_count") or 0),
                        }
                    )
    except sqlite3.Error:
        artifact_available = False

    languages = sorted(language_metrics.keys())
    rows: list[LanguageMetrics] = []
    for language in languages:
        current = language_metrics[language]
        call_totals = call_site_totals.get(
            language,
            {"eligible": 0, "accepted": 0, "dropped": 0},
        )
        rows.append(
            LanguageMetrics(
                language=language,
                files=current.files,
                nodes=current.nodes,
                edges=current.edges,
                call_sites_eligible=call_totals.get("eligible")
                if artifact_available
                else None,
                call_sites_accepted=call_totals.get("accepted")
                if artifact_available
                else None,
                call_sites_dropped=call_totals.get("dropped")
                if artifact_available
                else None,
                drop_reasons=call_site_reasons.get(language, {}),
                drop_classification=drop_classification.get(language, {}),
                drop_classification_by_scope=drop_classification_by_scope.get(
                    language, {}
                ),
                drop_reason_examples=call_site_reason_examples.get(language, {}),
                accepted_examples=call_site_accept_examples.get(language, []),
            )
        )

    total_files = sum(item.files for item in rows)
    total_nodes = sum(item.nodes for item in rows)
    total_edges = sum(item.edges for item in rows)
    total_eligible = (
        sum(item.call_sites_eligible or 0 for item in rows) if artifact_available else None
    )
    total_accepted = (
        sum(item.call_sites_accepted or 0 for item in rows) if artifact_available else None
    )
    total_dropped = (
        sum(item.call_sites_dropped or 0 for item in rows) if artifact_available else None
    )

    payload: dict[str, object] = {
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "artifact_db_available": artifact_available,
        "languages": [
            item.to_payload(include_failure_reasons=include_failure_reasons)
            for item in rows
        ],
        "totals": {
            "files": total_files,
            "nodes": total_nodes,
            "edges": total_edges,
            "call_sites": _call_sites_payload(total_eligible, total_accepted, total_dropped),
            "call_sites_by_scope": _scope_call_sites_payload(
                {
                    "non_tests": _sum_scope(
                        call_site_scope_totals, scope_key="non_tests", field_names=("eligible", "accepted", "dropped")
                    ),
                    "tests": _sum_scope(
                        call_site_scope_totals, scope_key="tests", field_names=("eligible", "accepted", "dropped")
                    ),
                }
                if artifact_available
                else None
            ),
        },
    }
    if include_failure_reasons and artifact_available:
        payload["totals"]["drop_classification"] = _sum_bucket_counts(drop_classification)
        payload["totals"]["drop_classification_by_scope"] = {
            "non_tests": _sum_bucket_counts_by_scope(
                drop_classification_by_scope, scope_key="non_tests"
            ),
            "tests": _sum_bucket_counts_by_scope(
                drop_classification_by_scope, scope_key="tests"
            ),
        }
    for item in payload["languages"]:
        language = str(item.get("language") or "")
        if not language:
            continue
        scope_counts = (
            call_site_scope_totals.get(
                language,
                {
                    "non_tests": {"eligible": 0, "accepted": 0, "dropped": 0},
                    "tests": {"eligible": 0, "accepted": 0, "dropped": 0},
                },
            )
            if artifact_available
            else None
        )
        item["call_sites_by_scope"] = _scope_call_sites_payload(scope_counts)
        item["adjusted_call_sites"] = _adjusted_call_sites_payload(
            item.get("call_sites"),
            excluded_external_likely=drop_classification.get(language, {}).get(
                "external_likely", 0
            ),
        )
        item["adjusted_call_sites_by_scope"] = _scope_adjusted_call_sites_payload(
            item.get("call_sites_by_scope"),
            excluded_non_tests=drop_classification_by_scope.get(language, {})
            .get("non_tests", {})
            .get("external_likely", 0),
            excluded_tests=drop_classification_by_scope.get(language, {})
            .get("tests", {})
            .get("external_likely", 0),
        )
        item["classification_quality"] = _classification_quality_payload(
            item.get("call_sites"),
            drop_reasons=call_site_reasons.get(language, {}),
            drop_classification=drop_classification.get(language, {}),
        )
        item["structural_density"] = _structural_density_payload(
            files=int(item.get("files") or 0),
            nodes=int(item.get("nodes") or 0),
            eligible_callsites=int((item.get("call_sites") or {}).get("eligible") or 0),
            file_node_distribution=file_node_distribution_by_language.get(language, []),
        )
    payload["totals"]["adjusted_call_sites"] = _adjusted_call_sites_payload(
        payload["totals"].get("call_sites"),
        excluded_external_likely=_sum_bucket_counts(drop_classification).get(
            "external_likely", 0
        ),
    )
    payload["totals"]["adjusted_call_sites_by_scope"] = _scope_adjusted_call_sites_payload(
        payload["totals"].get("call_sites_by_scope"),
        excluded_non_tests=_sum_bucket_counts_by_scope(
            drop_classification_by_scope, scope_key="non_tests"
        ).get("external_likely", 0),
        excluded_tests=_sum_bucket_counts_by_scope(
            drop_classification_by_scope, scope_key="tests"
        ).get("external_likely", 0),
    )
    payload["totals"]["classification_quality"] = _classification_quality_payload(
        payload["totals"].get("call_sites"),
        drop_reasons=_sum_bucket_counts(call_site_reasons),
        drop_classification=_sum_bucket_counts(drop_classification),
    )
    all_distribution: list[tuple[str, int]] = []
    for items in file_node_distribution_by_language.values():
        all_distribution.extend(items)
    payload["totals"]["structural_density"] = _structural_density_payload(
        files=int(payload["totals"].get("files") or 0),
        nodes=int(payload["totals"].get("nodes") or 0),
        eligible_callsites=int((payload["totals"].get("call_sites") or {}).get("eligible") or 0),
        file_node_distribution=all_distribution,
    )
    if include_failure_reasons:
        payload["failure_hotspots"] = {
            "top_failed_callers": {
                language: _top_items(counts, limit=10)
                for language, counts in sorted(failure_hotspots_callers.items())
            },
            "top_failed_files": {
                language: _top_items(counts, limit=10)
                for language, counts in sorted(failure_hotspots_files.items())
            },
        }
    return payload


def _call_sites_payload(
    eligible: int | None,
    accepted: int | None,
    dropped: int | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "eligible": eligible,
        "accepted": accepted,
        "dropped": dropped,
        "success_rate": None,
    }
    if eligible is None or accepted is None:
        return payload
    if eligible > 0:
        payload["success_rate"] = accepted / eligible
    return payload


def _adjusted_call_sites_payload(
    call_sites: dict[str, object] | None,
    *,
    excluded_external_likely: int,
) -> dict[str, object]:
    eligible = call_sites.get("eligible") if call_sites else None
    accepted = call_sites.get("accepted") if call_sites else None
    adjusted_eligible = None
    success_rate = None
    if isinstance(eligible, int):
        adjusted_eligible = max(eligible - int(excluded_external_likely or 0), 0)
    if isinstance(adjusted_eligible, int) and adjusted_eligible > 0 and isinstance(accepted, int):
        success_rate = accepted / adjusted_eligible
    return {
        "eligible": eligible,
        "accepted": accepted,
        "excluded_external_likely": int(excluded_external_likely or 0),
        "adjusted_eligible": adjusted_eligible,
        "success_rate": success_rate,
    }


def _top_items(items: dict[str, int], *, limit: int) -> list[dict[str, object]]:
    ordered = sorted(items.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [{"name": name, "count": int(count)} for name, count in ordered]


def _scope_bucket(file_path: str) -> str:
    if not file_path:
        return "non_tests"
    parts = [segment for segment in file_path.replace("\\", "/").split("/") if segment]
    return "tests" if any(part in {"test", "tests"} for part in parts) else "non_tests"


def _scope_call_sites_payload(
    scope_counts: dict[str, dict[str, int]] | None,
) -> dict[str, dict[str, object]] | None:
    if scope_counts is None:
        return None
    payload: dict[str, dict[str, object]] = {}
    for scope_key in ("non_tests", "tests"):
        counts = scope_counts.get(scope_key, {"eligible": 0, "accepted": 0, "dropped": 0})
        payload[scope_key] = _call_sites_payload(
            int(counts.get("eligible", 0)),
            int(counts.get("accepted", 0)),
            int(counts.get("dropped", 0)),
        )
    return payload


def _scope_adjusted_call_sites_payload(
    scope_payload: dict[str, dict[str, object]] | None,
    *,
    excluded_non_tests: int,
    excluded_tests: int,
) -> dict[str, dict[str, object]] | None:
    if not scope_payload:
        return None
    non_tests = _adjusted_call_sites_payload(
        scope_payload.get("non_tests"),
        excluded_external_likely=excluded_non_tests,
    )
    tests = _adjusted_call_sites_payload(
        scope_payload.get("tests"),
        excluded_external_likely=excluded_tests,
    )
    return {"non_tests": non_tests, "tests": tests}


def _classification_quality_payload(
    call_sites: dict[str, object] | None,
    *,
    drop_reasons: dict[str, int],
    drop_classification: dict[str, int],
) -> dict[str, object]:
    dropped = int((call_sites or {}).get("dropped") or 0)
    external_likely = int(drop_classification.get("external_likely", 0))
    ambiguous = int(
        drop_reasons.get("ambiguous_no_in_scope_candidate", 0)
        + drop_reasons.get("ambiguous_multiple_in_scope_candidates", 0)
    )
    external_share = (external_likely / dropped) if dropped > 0 else None
    ambiguous_share = (ambiguous / dropped) if dropped > 0 else None
    confidence = "n/a"
    caveats: list[str] = []
    if dropped > 0:
        confidence = "high"
        if external_share is not None and external_share >= 0.75:
            confidence = "low"
            caveats.append("external_likely_dominates_drops")
        elif external_share is not None and external_share >= 0.40:
            confidence = "medium"
            caveats.append("external_likely_material_share")
        if ambiguous_share is not None and ambiguous_share >= 0.75:
            confidence = "low"
            caveats.append("ambiguity_dominates_drops")
        elif ambiguous_share is not None and ambiguous_share >= 0.40:
            if confidence == "high":
                confidence = "medium"
            caveats.append("ambiguity_material_share")
    return {
        "dropped_callsites": dropped,
        "external_likely": external_likely,
        "ambiguous_drops": ambiguous,
        "external_likely_share": external_share,
        "ambiguous_share": ambiguous_share,
        "confidence": confidence,
        "caveats": caveats,
    }


def _structural_density_payload(
    *,
    files: int,
    nodes: int,
    eligible_callsites: int,
    file_node_distribution: list[tuple[str, int]],
) -> dict[str, object]:
    nodes_per_file = (nodes / files) if files > 0 else None
    eligible_callsites_per_file = (eligible_callsites / files) if files > 0 else None
    low_node_files = [(path, count) for path, count in file_node_distribution if count <= 1]
    low_node_dir_counts: dict[str, int] = {}
    for file_path, _count in low_node_files:
        bucket = _directory_bucket(file_path)
        low_node_dir_counts[bucket] = low_node_dir_counts.get(bucket, 0) + 1
    top_low_node_dirs = _top_items(low_node_dir_counts, limit=5)
    return {
        "files": files,
        "nodes": nodes,
        "eligible_callsites": eligible_callsites,
        "nodes_per_file": nodes_per_file,
        "eligible_callsites_per_file": eligible_callsites_per_file,
        "low_node_files_leq_1": len(low_node_files),
        "top_low_node_dirs": top_low_node_dirs,
        "zero_node_files_observed": 0,
        "zero_node_files_note": "Not observable from indexed files; files without nodes are not materialized in node_instances.",
    }


def _directory_bucket(file_path: str) -> str:
    normalized = file_path.replace("\\", "/").strip("/")
    if not normalized:
        return "."
    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return "."
    if len(parts) == 1:
        return parts[0]
    return "/".join(parts[:2])


def _drop_classification_bucket(
    *,
    identifier: str,
    drop_reason: str,
    candidate_count: int,
    callee_kind: str,
    known_callable_identifiers: set[str],
) -> str | None:
    if (
        drop_reason == "ambiguous_no_in_scope_candidate"
        and callee_kind == "qualified"
        and candidate_count >= 3
        and "." in identifier
    ):
        if _identifier_has_in_repo_callable(
            identifier,
            known_callable_identifiers=known_callable_identifiers,
        ):
            return "in_repo_unresolvable"
        return "external_likely"
    return None


def _build_callable_identifier_index(
    caller_metadata: dict[str, dict[str, object]],
) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for meta in caller_metadata.values():
        if str(meta.get("node_type") or "") != "callable":
            continue
        language = str(meta.get("language") or "")
        qualified_name = str(meta.get("qualified_name") or "")
        if not language or not qualified_name:
            continue
        index[language].add(qualified_name)
        terminal = _identifier_terminal(qualified_name)
        if terminal:
            index[language].add(terminal)
    return dict(index)


def _identifier_has_in_repo_callable(
    identifier: str,
    *,
    known_callable_identifiers: set[str],
) -> bool:
    if not identifier or not known_callable_identifiers:
        return False
    if identifier in known_callable_identifiers:
        return True
    terminal = _identifier_terminal(identifier)
    if not terminal:
        return False
    return terminal in known_callable_identifiers


def _identifier_terminal(identifier: str) -> str:
    text = identifier.strip()
    if not text:
        return ""
    return text.rsplit(".", 1)[-1].strip()


def _sum_bucket_counts(
    language_buckets: dict[str, dict[str, int]],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for buckets in language_buckets.values():
        for bucket, count in buckets.items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


def _sum_bucket_counts_by_scope(
    language_scope_buckets: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for scope_map in language_scope_buckets.values():
        for bucket, count in (scope_map.get(scope_key) or {}).items():
            totals[bucket] = totals.get(bucket, 0) + int(count)
    return dict(sorted(totals.items()))


def _sum_scope(
    language_scope_totals: dict[str, dict[str, dict[str, int]]],
    *,
    scope_key: str,
    field_names: tuple[str, ...],
) -> dict[str, int]:
    result = {field: 0 for field in field_names}
    for scope_counts in language_scope_totals.values():
        scope = scope_counts.get(scope_key, {})
        for field in field_names:
            result[field] += int(scope.get(field, 0))
    return result


__all__ = ["snapshot_report"]
