# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diagnostic-only pre-persist classification pipeline."""

from __future__ import annotations

from typing import Sequence

from ...artifacts.call_resolution import (
    build_module_binding_index,
    build_module_context,
    build_symbol_index,
    build_typescript_barrel_export_map,
    bounded_module_reachability,
    resolve_callees,
    simple_identifier,
)
from ...tools.call_extraction import CallExtractionRecord, PrePersistObservation
from ....data_storage.core_db import read_ops as core_read
from ....pipelines.progress import ProgressFactory
from ....pipelines.exec.reporting_callsites import scope_bucket
from .classifier import (
    classify_no_in_repo_candidate,
    classify_positive_candidate_rejection,
)
from .models import (
    DiagnosticAggregation,
    DiagnosticClassification,
    DiagnosticMissObservation,
)
from .report import empty_diagnostic_buckets


def classify_pre_persist_misses(
    *,
    core_conn,
    snapshot_id: str,
    call_records: Sequence[CallExtractionRecord],
    progress_factory: ProgressFactory | None = None,
) -> dict[str, object]:
    if not call_records:
        return {
            "totals": empty_diagnostic_buckets(),
            "by_language": {},
            "by_scope": {
                "non_tests": empty_diagnostic_buckets(),
                "tests": empty_diagnostic_buckets(),
            },
            "observations": [],
        }
    symbol_index, _in_repo_callable_ids, callable_qname_by_id = build_symbol_index(
        core_conn, snapshot_id
    )
    (
        module_lookup,
        import_targets,
        expanded_import_targets,
        module_ancestors,
        module_file_by_name,
    ) = build_module_context(core_conn, snapshot_id)
    caller_metadata = core_read.caller_node_metadata_map(core_conn, snapshot_id)
    caller_language_map = core_read.caller_language_map(core_conn, snapshot_id)
    repo_module_prefixes = _repo_module_prefixes(module_file_by_name)
    module_bindings_by_name = build_module_binding_index(
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
        simple_identifier=simple_identifier,
    )
    ts_barrel_export_map = build_typescript_barrel_export_map(
        import_targets=import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
        bounded_module_reachability=bounded_module_reachability,
    )
    aggregation = DiagnosticAggregation(
        totals=empty_diagnostic_buckets(),
        by_scope={
            "non_tests": empty_diagnostic_buckets(),
            "tests": empty_diagnostic_buckets(),
        },
    )
    progress_handle = (
        progress_factory("Diagnostic classification", len(call_records))
        if progress_factory is not None
        else None
    )
    for record in call_records:
        caller_id = record.caller_structural_id
        caller_module = module_lookup.get(caller_id)
        observations: list[PrePersistObservation] = []
        resolve_callees(
            record.callee_identifiers,
            symbol_index,
            caller_module=caller_module,
            caller_language=caller_language_map.get(caller_id),
            module_lookup=module_lookup,
            callable_qname_by_id=callable_qname_by_id,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_ancestors=module_ancestors,
            module_bindings_by_name=module_bindings_by_name,
            module_file_by_name=module_file_by_name,
            ts_barrel_export_map=ts_barrel_export_map,
            pre_persist_observations=observations,
            local_binding_facts=record.local_binding_facts,
        )
        caller_info = caller_metadata.get(caller_id) or {}
        language = str(
            caller_info.get("language") or caller_language_map.get(caller_id) or "unknown"
        )
        file_path = str(caller_info.get("file_path") or "")
        scope_key = scope_bucket(file_path)
        for item in observations:
            prefix_matches = _repo_prefix_matches(item.identifier, repo_module_prefixes)
            reachable_modules = _reachable_repo_modules(
                caller_module=caller_module,
                import_targets=import_targets,
                expanded_import_targets=expanded_import_targets,
                module_ancestors=module_ancestors,
                ts_barrel_export_map=ts_barrel_export_map,
            )
            reachable_prefixes = _module_prefixes(reachable_modules)
            reachable_prefix_matches = _repo_prefix_matches(
                item.identifier,
                reachable_prefixes,
            )
            terminal = item.identifier.rsplit(".", 1)[-1].strip()
            observation = DiagnosticMissObservation(
                language=language,
                file_path=file_path,
                caller_structural_id=caller_id,
                caller_qualified_name=record.caller_qualified_name,
                caller_module=caller_module,
                identifier=item.identifier,
                ordinal=item.ordinal,
                callee_kind=item.callee_kind,
                candidate_module_hints=item.candidate_module_hints,
                repo_prefix_matches=prefix_matches,
                longest_repo_prefix_match=prefix_matches[-1] if prefix_matches else "",
                repo_prefix_match_depth=len(prefix_matches),
                reachable_repo_prefix_matches=reachable_prefix_matches,
                longest_reachable_repo_prefix_match=(
                    reachable_prefix_matches[-1] if reachable_prefix_matches else ""
                ),
                reachable_repo_binding=any(
                    terminal in module_bindings_by_name.get(module_name, set())
                    for module_name in reachable_modules
                ),
                repo_hint_overlap=_repo_hint_overlap(
                    item.candidate_module_hints,
                    repo_module_prefixes,
                ),
                identifier_root=_identifier_root(item.identifier),
                local_binding_symbol=item.local_binding_symbol,
                local_binding_target=item.local_binding_target,
                local_binding_kind=item.local_binding_kind,
                local_binding_evidence_kind=item.local_binding_evidence_kind,
            )
            classified = classify_no_in_repo_candidate(observation)
            _inc_bucket(aggregation.totals, classified.bucket)
            language_buckets = aggregation.by_language.setdefault(
                language,
                empty_diagnostic_buckets(),
            )
            _inc_bucket(language_buckets, classified.bucket)
            _inc_bucket(aggregation.by_scope[scope_key], classified.bucket)
            aggregation.observations.append(
                {
                    "bucket": classified.bucket,
                    "reasons": list(classified.reasons),
                    "signals": _signals_for_observation(observation, classified.reasons),
                    "language": observation.language,
                    "file_path": observation.file_path,
                    "caller_structural_id": observation.caller_structural_id,
                    "caller_qualified_name": observation.caller_qualified_name,
                    "caller_module": observation.caller_module,
                    "identifier": observation.identifier,
                    "identifier_root": observation.identifier_root,
                    "ordinal": observation.ordinal,
                    "callee_kind": observation.callee_kind,
                    "candidate_module_hints": list(observation.candidate_module_hints),
                    "repo_prefix_matches": list(observation.repo_prefix_matches),
                    "longest_repo_prefix_match": observation.longest_repo_prefix_match,
                    "repo_prefix_match_depth": observation.repo_prefix_match_depth,
                    "reachable_repo_prefix_matches": list(
                        observation.reachable_repo_prefix_matches
                    ),
                    "longest_reachable_repo_prefix_match": (
                        observation.longest_reachable_repo_prefix_match
                    ),
                    "reachable_repo_binding": observation.reachable_repo_binding,
                    "repo_hint_overlap": list(observation.repo_hint_overlap),
                    "local_binding_symbol": observation.local_binding_symbol,
                    "local_binding_target": observation.local_binding_target,
                    "local_binding_kind": observation.local_binding_kind,
                    "local_binding_evidence_kind": (
                        observation.local_binding_evidence_kind
                    ),
                    "scope": scope_key,
                }
            )
        if progress_handle is not None:
            progress_handle.advance(1)
    if progress_handle is not None:
        progress_handle.close()
    return {
        "totals": aggregation.totals,
        "by_language": aggregation.by_language,
        "by_scope": aggregation.by_scope,
        "observations": aggregation.observations,
    }


def classify_rejected_calls(
    *,
    core_conn,
    artifact_conn,
    snapshot_id: str,
    progress_factory: ProgressFactory | None = None,
) -> dict[str, object]:
    rows = artifact_conn.execute(
        """
        SELECT
            caller_structural_id,
            caller_qualified_name,
            caller_module,
            caller_language,
            caller_file_path,
            identifier,
            call_ordinal,
            callee_kind,
            candidate_module_hints,
            local_binding_symbol,
            local_binding_target,
            local_binding_kind,
            local_binding_evidence_kind,
            gate_reason,
            raw_drop_reason
        FROM rejected_callsites_temp
        ORDER BY rowid
        """
    ).fetchall()
    if not rows:
        return {
            "totals": empty_diagnostic_buckets(),
            "by_language": {},
            "by_scope": {
                "non_tests": empty_diagnostic_buckets(),
                "tests": empty_diagnostic_buckets(),
            },
            "observations": [],
        }
    symbol_index, _in_repo_callable_ids, callable_qname_by_id = build_symbol_index(
        core_conn, snapshot_id
    )
    (
        module_lookup,
        import_targets,
        expanded_import_targets,
        module_ancestors,
        module_file_by_name,
    ) = build_module_context(core_conn, snapshot_id)
    repo_module_prefixes = _repo_module_prefixes(module_file_by_name)
    module_bindings_by_name = build_module_binding_index(
        callable_qname_by_id=callable_qname_by_id,
        module_lookup=module_lookup,
        simple_identifier=simple_identifier,
    )
    ts_barrel_export_map = build_typescript_barrel_export_map(
        import_targets=import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
        bounded_module_reachability=bounded_module_reachability,
    )
    aggregation = DiagnosticAggregation(
        totals=empty_diagnostic_buckets(),
        by_scope={
            "non_tests": empty_diagnostic_buckets(),
            "tests": empty_diagnostic_buckets(),
        },
    )
    progress_handle = (
        progress_factory("Diagnostic classification", len(rows))
        if progress_factory is not None
        else None
    )
    for row in rows:
        caller_module = str(row["caller_module"]) if row["caller_module"] is not None else None
        identifier = str(row["identifier"] or "")
        candidate_module_hints = _split_candidate_module_hints(
            row["candidate_module_hints"]
        )
        prefix_matches = _repo_prefix_matches(identifier, repo_module_prefixes)
        reachable_modules = _reachable_repo_modules(
            caller_module=caller_module,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_ancestors=module_ancestors,
            ts_barrel_export_map=ts_barrel_export_map,
        )
        reachable_prefixes = _module_prefixes(reachable_modules)
        reachable_prefix_matches = _repo_prefix_matches(identifier, reachable_prefixes)
        terminal = identifier.rsplit(".", 1)[-1].strip()
        observation = DiagnosticMissObservation(
            language=str(row["caller_language"] or "unknown"),
            file_path=str(row["caller_file_path"] or ""),
            caller_structural_id=str(row["caller_structural_id"] or ""),
            caller_qualified_name=str(row["caller_qualified_name"] or ""),
            caller_module=caller_module,
            identifier=identifier,
            ordinal=int(row["call_ordinal"] or 0),
            callee_kind=str(row["callee_kind"] or "unknown"),
            candidate_module_hints=candidate_module_hints,
            repo_prefix_matches=prefix_matches,
            longest_repo_prefix_match=prefix_matches[-1] if prefix_matches else "",
            repo_prefix_match_depth=len(prefix_matches),
            reachable_repo_prefix_matches=reachable_prefix_matches,
            longest_reachable_repo_prefix_match=(
                reachable_prefix_matches[-1] if reachable_prefix_matches else ""
            ),
            reachable_repo_binding=any(
                terminal in module_bindings_by_name.get(module_name, set())
                for module_name in reachable_modules
            ),
            repo_hint_overlap=_repo_hint_overlap(
                candidate_module_hints,
                repo_module_prefixes,
            ),
            identifier_root=_identifier_root(identifier),
            local_binding_symbol=str(row["local_binding_symbol"] or ""),
            local_binding_target=str(row["local_binding_target"] or ""),
            local_binding_kind=str(row["local_binding_kind"] or ""),
            local_binding_evidence_kind=str(row["local_binding_evidence_kind"] or ""),
            gate_reason=str(row["gate_reason"] or ""),
            raw_drop_reason=str(row["raw_drop_reason"] or ""),
        )
        classified = _classify_rejected_observation(observation)
        language = observation.language
        scope_key = scope_bucket(observation.file_path)
        _inc_bucket(aggregation.totals, classified.bucket)
        language_buckets = aggregation.by_language.setdefault(
            language,
            empty_diagnostic_buckets(),
        )
        _inc_bucket(language_buckets, classified.bucket)
        _inc_bucket(aggregation.by_scope[scope_key], classified.bucket)
        signals = _signals_for_observation(observation, classified.reasons)
        if observation.gate_reason:
            signals.append(f"gate_reason:{observation.gate_reason}")
        if observation.raw_drop_reason:
            signals.append(f"raw_drop_reason:{observation.raw_drop_reason}")
        aggregation.observations.append(
            {
                "bucket": classified.bucket,
                "reasons": list(classified.reasons),
                "signals": signals,
                "language": observation.language,
                "file_path": observation.file_path,
                "caller_structural_id": observation.caller_structural_id,
                "caller_qualified_name": observation.caller_qualified_name,
                "caller_module": observation.caller_module,
                "identifier": observation.identifier,
                "identifier_root": observation.identifier_root,
                "ordinal": observation.ordinal,
                "callee_kind": observation.callee_kind,
                "candidate_module_hints": list(observation.candidate_module_hints),
                "repo_prefix_matches": list(observation.repo_prefix_matches),
                "longest_repo_prefix_match": observation.longest_repo_prefix_match,
                "repo_prefix_match_depth": observation.repo_prefix_match_depth,
                "reachable_repo_prefix_matches": list(
                    observation.reachable_repo_prefix_matches
                ),
                "longest_reachable_repo_prefix_match": (
                    observation.longest_reachable_repo_prefix_match
                ),
                "reachable_repo_binding": observation.reachable_repo_binding,
                "repo_hint_overlap": list(observation.repo_hint_overlap),
                "local_binding_symbol": observation.local_binding_symbol,
                "local_binding_target": observation.local_binding_target,
                "local_binding_kind": observation.local_binding_kind,
                "local_binding_evidence_kind": (
                    observation.local_binding_evidence_kind
                ),
                "scope": scope_key,
                "gate_reason": observation.gate_reason,
                "raw_drop_reason": observation.raw_drop_reason,
            }
        )
        if progress_handle is not None:
            progress_handle.advance(1)
    if progress_handle is not None:
        progress_handle.close()
    return {
        "totals": aggregation.totals,
        "by_language": aggregation.by_language,
        "by_scope": aggregation.by_scope,
        "observations": aggregation.observations,
    }


def merge_diagnostic_payloads(
    *payloads: dict[str, object] | None,
) -> dict[str, object]:
    merged = {
        "totals": empty_diagnostic_buckets(),
        "by_language": {},
        "by_scope": {
            "non_tests": empty_diagnostic_buckets(),
            "tests": empty_diagnostic_buckets(),
        },
        "observations": [],
    }
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        _merge_bucket_counts(
            merged["totals"],
            payload.get("totals"),
        )
        by_language = payload.get("by_language")
        if isinstance(by_language, dict):
            for language, buckets in by_language.items():
                if not isinstance(language, str):
                    continue
                target = merged["by_language"].setdefault(
                    language,
                    empty_diagnostic_buckets(),
                )
                _merge_bucket_counts(target, buckets)
        by_scope = payload.get("by_scope")
        if isinstance(by_scope, dict):
            for scope_key, buckets in by_scope.items():
                if scope_key not in {"non_tests", "tests"}:
                    continue
                _merge_bucket_counts(merged["by_scope"][scope_key], buckets)
        observations = payload.get("observations")
        if isinstance(observations, list):
            merged["observations"].extend(
                item for item in observations if isinstance(item, dict)
            )
    return merged


def _inc_bucket(target: dict[str, int], bucket: str) -> None:
    target[bucket] = int(target.get(bucket, 0)) + 1


def _merge_bucket_counts(target: dict[str, int], source: object) -> None:
    if not isinstance(source, dict):
        return
    for bucket, count in source.items():
        if not isinstance(bucket, str):
            continue
        target[bucket] = int(target.get(bucket, 0)) + int(count or 0)


def _identifier_root(identifier: str) -> str:
    return identifier.split(".", 1)[0].strip()


def _split_candidate_module_hints(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def _classify_rejected_observation(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    if observation.gate_reason in {"accepted_outside_in_repo", "invalid_observation_shape"}:
        return DiagnosticClassification(
            bucket=observation.gate_reason,
            reasons=(f"gate:{observation.gate_reason}",),
        )
    if observation.gate_reason == "no_in_repo_candidate":
        return classify_no_in_repo_candidate(observation)
    return classify_positive_candidate_rejection(observation)


def _repo_module_prefixes(module_file_by_name: dict[str, str]) -> set[str]:
    return _module_prefixes(module_file_by_name)


def _module_prefixes(module_names: Sequence[str] | set[str] | dict[str, str]) -> set[str]:
    prefixes: set[str] = set()
    for module_name in module_names:
        parts = [part for part in str(module_name).split(".") if part]
        for idx in range(1, len(parts) + 1):
            prefixes.add(".".join(parts[:idx]))
    return prefixes


def _repo_prefix_matches(identifier: str, repo_module_prefixes: set[str]) -> tuple[str, ...]:
    parts = [part for part in str(identifier).split(".") if part]
    matches: list[str] = []
    for idx in range(1, len(parts)):
        prefix = ".".join(parts[:idx])
        if prefix in repo_module_prefixes:
            matches.append(prefix)
    return tuple(matches)


def _signals_for_observation(
    observation: DiagnosticMissObservation,
    reasons: tuple[str, ...],
) -> list[str]:
    signals: set[str] = set()
    identifier_parts = [part for part in observation.identifier.split(".") if part]
    if identifier_parts:
        signals.add(f"identifier_depth:{len(identifier_parts)}")
    if observation.repo_prefix_matches:
        signals.add("repo_owned_prefix")
        signals.add(f"repo_prefix_depth:{observation.repo_prefix_match_depth}")
        if observation.longest_repo_prefix_match:
            signals.add("deep_repo_prefix" if observation.repo_prefix_match_depth > 1 else "shallow_repo_prefix")
    else:
        signals.add("non_repo_root")
    if observation.callee_kind == "qualified":
        signals.add("qualified_identifier")
    else:
        signals.add("terminal_identifier")
    if observation.candidate_module_hints:
        signals.add("candidate_module_hint")
        signals.add(f"candidate_hint_count:{len(observation.candidate_module_hints)}")
    if observation.reachable_repo_prefix_matches:
        signals.add("reachable_repo_prefix")
    if observation.longest_reachable_repo_prefix_match:
        signals.add(
            f"reachable_repo_prefix_depth:{len(observation.longest_reachable_repo_prefix_match.split('.'))}"
        )
    if observation.reachable_repo_binding:
        signals.add("reachable_repo_binding")
    if observation.local_binding_target:
        signals.add("local_binding_target")
        if observation.local_binding_kind:
            signals.add(f"local_binding_kind:{observation.local_binding_kind}")
    if observation.local_binding_symbol:
        signals.add("local_binding_symbol")
    if observation.repo_prefix_matches and not observation.reachable_repo_prefix_matches:
        signals.add("unreachable_repo_prefix")
    if observation.repo_hint_overlap:
        signals.add("repo_hint_overlap")
        signals.add(f"repo_hint_overlap_count:{len(observation.repo_hint_overlap)}")
    elif observation.candidate_module_hints:
        signals.add("external_module_hint")
    if len(identifier_parts) >= 2:
        owner = identifier_parts[-2]
        signals.add(
            "owner_segment:type_like"
            if owner[:1].isupper() or owner.isupper()
            else "owner_segment:value_like"
        )
    if any(reason.endswith("_member_terminal") for reason in reasons):
        signals.add("member_terminal")
    if any("receiver" in reason for reason in reasons):
        signals.add("receiver_special_form")
    if "dynamic_member_terminal" in reasons:
        signals.add("receiver_unknown")
    if "repeated_qualified_segment" in reasons:
        signals.add("repeated_segment")
    if any("builtin" in reason or "stdlib" in reason or "global" in reason for reason in reasons):
        signals.add("runtime_namespace_root")
    return sorted(signals)


def _reachable_repo_modules(
    *,
    caller_module: str | None,
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_ancestors: dict[str, set[str]],
    ts_barrel_export_map: dict[str, set[str]],
) -> set[str]:
    if not caller_module:
        return set()
    reachable: set[str] = {caller_module}
    reachable.update(module_ancestors.get(caller_module, set()))
    direct_targets = set(import_targets.get(caller_module, set()))
    expanded_targets = set(expanded_import_targets.get(caller_module, set()))
    reachable.update(direct_targets)
    reachable.update(expanded_targets)
    for module_name in {caller_module, *direct_targets, *expanded_targets}:
        reachable.update(ts_barrel_export_map.get(module_name, set()))
    return reachable


def _repo_hint_overlap(
    candidate_module_hints: Sequence[str],
    repo_module_prefixes: set[str],
) -> tuple[str, ...]:
    matches: set[str] = set()
    for hint in candidate_module_hints:
        hint_str = str(hint).strip()
        if not hint_str:
            continue
        for idx in range(1, len(hint_str.split(".")) + 1):
            prefix = ".".join(hint_str.split(".")[:idx])
            if prefix in repo_module_prefixes:
                matches.add(hint_str)
                break
    return tuple(sorted(matches))
