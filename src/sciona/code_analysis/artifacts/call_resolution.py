# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Artifact call resolution helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping, Sequence, cast

from ..analysis.module_id import module_id_for
from ..contracts.enforcement import (
    StrictCallDecision,
    build_strict_resolution_stats,
    record_strict_resolution_decision,
    resolve_strict_call_batch,
)
from ..core.structural_assembler_index import expand_import_targets
from ..config import CALLABLE_NODE_TYPES
from ..languages.common.ir import (
    LocalBindingFact,
    binding_candidate_qnames_for_identifier,
    binding_match_for_identifier,
)
from ..core.extract.calls.types import RejectedObservation
from ...data_storage.core_db import read_ops as core_read
from .call_resolution_python import (
    build_module_binding_index,
    resolve_python_export_chain_ambiguous,
)
from .call_resolution_typescript import (
    build_typescript_barrel_export_map,
    resolve_typescript_barrel_ambiguous,
)

from .call_resolution_javascript import (
    build_javascript_barrel_export_map,
    resolve_javascript_structural_ambiguous,
)
from .in_repo_static_gate import (
    evaluate_callsite_row_for_persistence,
    normalized_non_accepted_gate_reason,
)


def build_symbol_index(
    core_conn, snapshot_id: str
) -> tuple[dict[str, list[str]], set[str], dict[str, str]]:
    callable_types = sorted(CALLABLE_NODE_TYPES)
    rows = core_read.list_nodes_by_types(core_conn, snapshot_id, callable_types)
    index_sets: dict[str, set[str]] = defaultdict(set)
    in_repo_callable_ids: set[str] = set()
    callable_qname_by_id: dict[str, str] = {}
    for structural_id, _node_type, qualified_name in rows:
        in_repo_callable_ids.add(structural_id)
        if not qualified_name:
            continue
        callable_qname_by_id[structural_id] = qualified_name
        terminal = simple_identifier(qualified_name)
        if terminal:
            index_sets[terminal].add(structural_id)
        index_sets[qualified_name].add(structural_id)
        if terminal in ('__new__', '__init__', 'new', 'constructor'):
            owner = qualified_name.rsplit('.', 1)[0]
            class_name = simple_identifier(owner)
            if class_name and owner.endswith(class_name):
                index_sets[class_name].add(structural_id)
    return (
        {key: sorted(values) for key, values in index_sets.items()},
        in_repo_callable_ids,
        callable_qname_by_id,
    )


def filter_in_repo_callsite_rows(
    rows: Sequence[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
    *,
    in_repo_callable_ids: set[str],
) -> tuple[
    list[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
    dict[str, int],
    list[tuple[CallsiteRow, str, str | None]],
]:
    filtered = []
    filtered_out: dict[str, int] = {}
    rejected_rows: list[tuple[CallsiteRow, str, str | None]] = []
    for row in rows:
        decision = evaluate_callsite_row_for_persistence(
            row,
            in_repo_callable_ids=in_repo_callable_ids,
        )
        if decision.persist:
            filtered.append(row)
            continue
        gate_reason = str(decision.gate_reason)
        _inc_non_accepted_gate_reason(filtered_out, gate_reason)
        rejected_rows.append((row, gate_reason, decision.raw_drop_reason))
    return filtered, filtered_out, rejected_rows


def _inc_non_accepted_gate_reason(target: dict[str, int], bucket: str) -> None:
    normalized = normalized_non_accepted_gate_reason(bucket)
    target[normalized] = int(target.get(normalized, 0)) + 1


def persisted_callsite_outcomes(
    rows: Sequence[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
    *,
    in_repo_callable_ids: set[str],
) -> tuple[
    set[str],
    list[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
    dict[str, int],
    list[tuple[CallsiteRow, str, str | None]],
]:
    """Return the persisted callsite rows and the accepted in-repo callees they imply."""

    filtered, filtered_out, rejected_rows = filter_in_repo_callsite_rows(
        rows,
        in_repo_callable_ids=in_repo_callable_ids,
    )
    persisted_callee_ids = {
        accepted_callee_id
        for _identifier, status, accepted_callee_id, _provenance, _drop_reason, *_rest in filtered
        if status == "accepted" and accepted_callee_id
    }
    return persisted_callee_ids, filtered, filtered_out, rejected_rows


def callsite_pair_rows(
    rows: Sequence[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
    *,
    in_repo_callable_ids: set[str],
    symbol_index: dict[str, Sequence[str]],
    caller_module: str | None,
    caller_language: str | None = None,
    module_lookup: dict[str, str],
    callable_qname_by_id: dict[str, str] | None = None,
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]] | None = None,
    module_ancestors: dict[str, set[str]],
) -> list[tuple[str, int, str, str]]:
    callable_qname_by_id = callable_qname_by_id or {}
    expanded_import_targets = expanded_import_targets or import_targets
    pair_rows: list[tuple[str, int, str, str]] = []
    for row in rows:
        (
            identifier,
            status,
            accepted_callee_id,
            _provenance,
            drop_reason,
            _candidate_count,
            _callee_kind,
            _call_start_byte,
            _call_end_byte,
            call_ordinal,
            _in_scope_candidate_count,
            _candidate_module_hints,
        ) = row
        if status == "accepted" and accepted_callee_id in in_repo_callable_ids:
            pair_rows.append(
                (identifier, int(call_ordinal), accepted_callee_id, "in_repo_candidate")
            )
            continue
        if drop_reason != "ambiguous_multiple_in_scope_candidates":
            continue
        pair_candidates = _pair_candidates_for_identifier(
            identifier=identifier,
            symbol_index=symbol_index,
            caller_module=caller_module,
            caller_language=caller_language,
            module_lookup=module_lookup,
            callable_qname_by_id=callable_qname_by_id,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_ancestors=module_ancestors,
        )
        for callee_id in pair_candidates:
            if callee_id in in_repo_callable_ids:
                pair_rows.append(
                    (identifier, int(call_ordinal), callee_id, "in_repo_candidate")
                )
    return pair_rows


def build_module_context(
    core_conn,
    snapshot_id: str,
) -> tuple[
    dict[str, str],
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, str],
]:
    node_rows = core_read.list_nodes_with_names(core_conn, snapshot_id)
    module_names = {
        qualified_name
        for _structural_id, node_type, qualified_name in node_rows
        if node_type == "module" and qualified_name
    }
    module_id_by_name = {
        qualified_name: structural_id
        for structural_id, node_type, qualified_name in node_rows
        if node_type == "module" and qualified_name
    }
    module_name_by_id = {
        structural_id: qualified_name
        for qualified_name, structural_id in module_id_by_name.items()
    }
    module_lookup: dict[str, str] = {}
    module_file_by_name: dict[str, str] = {}
    node_meta = core_read.caller_node_metadata_map(core_conn, snapshot_id)
    for structural_id, _node_type, qualified_name in node_rows:
        if not qualified_name:
            continue
        module_name = module_id_for(qualified_name, module_names)
        if module_name:
            module_lookup[structural_id] = module_name
        if structural_id in module_id_by_name.values():
            file_path = str((node_meta.get(structural_id) or {}).get("file_path") or "")
            if file_path:
                module_file_by_name[qualified_name] = file_path
    module_ids = set(module_id_by_name.values())
    direct_import_targets: dict[str, set[str]] = defaultdict(set)
    for src_id, dst_id in core_read.list_edges_by_type(
        core_conn, snapshot_id, "IMPORTS_DECLARED"
    ):
        if src_id in module_ids and dst_id in module_ids:
            src_name = module_name_by_id.get(src_id)
            dst_name = module_name_by_id.get(dst_id)
            if src_name and dst_name:
                direct_import_targets[src_name].add(dst_name)
    import_targets = {
        module_name: set(targets) for module_name, targets in direct_import_targets.items()
    }
    expanded_import_targets = expand_import_targets(import_targets)
    module_ancestors = {
        module_name: module_qname_ancestors(module_name) for module_name in module_names
    }
    return (
        module_lookup,
        import_targets,
        expanded_import_targets,
        module_ancestors,
        module_file_by_name,
    )


def load_node_hashes(
    core_conn, snapshot_id: str, node_ids: Iterable[str]
) -> dict[str, str]:
    return core_read.node_hashes_for_ids(core_conn, snapshot_id, node_ids)


def resolve_callees(
    identifiers: Sequence[str],
    symbol_index: dict[str, Sequence[str]],
    *,
    caller_module: str | None,
    caller_language: str | None = None,
    module_lookup: dict[str, str],
    callable_qname_by_id: dict[str, str] | None = None,
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]] | None = None,
    module_ancestors: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]] | None = None,
    module_file_by_name: dict[str, str] | None = None,
    ts_barrel_export_map: dict[str, set[str]] | None = None,
    js_barrel_export_map: dict[str, set[str]] | None = None,
    rejected_observations: list[RejectedObservation] | None = None,
    local_binding_facts: Sequence[LocalBindingFact] = (),
) -> tuple[
    set[str],
    set[str],
    dict[str, object],
    list[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ],
]:
    callable_qname_by_id = callable_qname_by_id or {}
    expanded_import_targets = expanded_import_targets or import_targets
    module_bindings_by_name = module_bindings_by_name or {}
    module_file_by_name = module_file_by_name or {}
    ts_barrel_export_map = ts_barrel_export_map or {}
    js_barrel_export_map = js_barrel_export_map or {}
    symbol_index = _apply_binding_fact_candidates(
        identifiers=identifiers,
        symbol_index=symbol_index,
        callable_qname_by_id=callable_qname_by_id,
        local_binding_facts=local_binding_facts,
    )
    resolved_ids: set[str] = set()
    resolved_names: set[str] = set()
    callsite_rows: list[
        tuple[
            str,
            str,
            str | None,
            str | None,
            str | None,
            int,
            str,
            int | None,
            int | None,
            int,
            int | None,
            str | None,
        ]
    ] = []
    stats = build_strict_resolution_stats()
    non_accepted_gate_reasons: dict[str, int] = {}
    strict_batch = resolve_strict_call_batch(
        identifiers,
        symbol_index=symbol_index,
        caller_module=caller_module,
        module_lookup=module_lookup,
        candidate_qualified_names=callable_qname_by_id,
        import_targets=import_targets,
        expanded_import_targets=expanded_import_targets,
        caller_ancestor_modules=module_ancestors.get(caller_module or "", set()),
        allow_descendant_scope_for_ambiguous=caller_language == "typescript",
    )
    for resolution in strict_batch.resolutions:
        identifier = resolution.identifier
        binding_match = binding_match_for_identifier(identifier, tuple(local_binding_facts))
        decision = resolution.decision
        rescue_candidate, rescue_provenance = _resolve_post_strict_rescue_candidate(
            identifier=identifier,
            decision=decision,
            symbol_index=symbol_index,
            caller_module=caller_module,
            caller_language=caller_language,
            callable_qname_by_id=callable_qname_by_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_bindings_by_name=module_bindings_by_name,
            module_file_by_name=module_file_by_name,
            ts_barrel_export_map=ts_barrel_export_map,
            js_barrel_export_map=js_barrel_export_map,
        )
        if rescue_candidate:
            if rescue_provenance == "export_chain_narrowed" and (
                caller_language in {"python", "typescript"}
                or (
                    caller_language == "javascript"
                    and decision.dropped_reason in {"unique_without_provenance", "no_candidates"}
                )
            ):
                decision = StrictCallDecision(
                    accepted_candidate=rescue_candidate,
                    accepted_provenance="import_narrowed",
                    dropped_reason=None,
                    candidate_count=max(1, int(decision.candidate_count)),
                    in_scope_candidate_count=1,
                    candidate_module_hints=tuple(decision.candidate_module_hints),
                )
            else:
                decision = _revalidate_rescue_candidate(
                    identifier=identifier,
                    rescue_candidate=rescue_candidate,
                    caller_module=caller_module,
                    caller_language=caller_language,
                    callable_qname_by_id=callable_qname_by_id,
                    module_lookup=module_lookup,
                    import_targets=import_targets,
                    expanded_import_targets=expanded_import_targets,
                    caller_ancestor_modules=module_ancestors.get(caller_module or "", set()),
                )
        ordinal = resolution.ordinal
        callee_kind = "qualified" if "." in identifier else "terminal"
        record_strict_resolution_decision(
            stats,
            decision,
            accepted_provenance=rescue_provenance,
        )
        if decision.candidate_count <= 0:
            _inc_non_accepted_gate_reason(
                non_accepted_gate_reasons,
                "no_in_repo_candidate",
            )
            if rejected_observations is not None:
                hints = tuple(str(item) for item in (decision.candidate_module_hints or ()))
                rejected_observations.append(
                    RejectedObservation(
                        identifier=identifier,
                        ordinal=ordinal,
                        callee_kind=callee_kind,
                        caller_language=caller_language,
                        caller_module=caller_module,
                        candidate_module_hints=hints,
                        local_binding_symbol=binding_match.symbol if binding_match else "",
                        local_binding_target=binding_match.target if binding_match else "",
                        local_binding_kind=(
                            binding_match.binding_kind if binding_match else ""
                        ),
                        local_binding_evidence_kind=(
                            binding_match.evidence_kind if binding_match else ""
                        ),
                    )
                )
        if decision.accepted_candidate:
            resolved_ids.add(decision.accepted_candidate)
            resolved_names.add(identifier)
            accepted_provenance = rescue_provenance or str(decision.accepted_provenance)
            if decision.candidate_count > 0:
                callsite_rows.append(
                    (
                        identifier,
                        "accepted",
                        decision.accepted_candidate,
                        accepted_provenance,
                        None,
                        decision.candidate_count,
                        callee_kind,
                        None,
                        None,
                        ordinal,
                        decision.in_scope_candidate_count,
                        ",".join(decision.candidate_module_hints)
                        if decision.candidate_module_hints
                        else None,
                    )
                )
            continue
        if decision.candidate_count > 0:
            callsite_rows.append(
                (
                    identifier,
                    "dropped",
                    None,
                    None,
                    decision.dropped_reason,
                    decision.candidate_count,
                    callee_kind,
                    None,
                    None,
                    ordinal,
                    decision.in_scope_candidate_count,
                    ",".join(decision.candidate_module_hints)
                    if decision.candidate_module_hints
                    else None,
                )
                )
    if non_accepted_gate_reasons:
        stats["non_accepted_gate_reasons"] = dict(non_accepted_gate_reasons)
    return resolved_ids, resolved_names, stats, callsite_rows


def _apply_binding_fact_candidates(
    *,
    identifiers: Sequence[str],
    symbol_index: Mapping[str, Sequence[str]],
    callable_qname_by_id: Mapping[str, str],
    local_binding_facts: Sequence[LocalBindingFact],
) -> dict[str, Sequence[str]]:
    if not identifiers or not local_binding_facts or not callable_qname_by_id:
        return dict(symbol_index)
    callable_ids_by_qname: dict[str, list[str]] = defaultdict(list)
    for callable_id, qname in callable_qname_by_id.items():
        if qname:
            callable_ids_by_qname[qname].append(callable_id)
    resolved_index: dict[str, Sequence[str]] = dict(symbol_index)
    for identifier in identifiers:
        binding_qnames = binding_candidate_qnames_for_identifier(
            identifier,
            tuple(local_binding_facts),
        )
        if not binding_qnames:
            continue
        binding_ids: list[str] = []
        for qname in binding_qnames:
            matches = callable_ids_by_qname.get(qname) or []
            if len(matches) == 1:
                binding_ids.append(matches[0])
        if not binding_ids:
            continue
        resolved_index[identifier] = tuple(dict.fromkeys(binding_ids))
    return resolved_index


def _pair_candidates_for_identifier(
    *,
    identifier: str,
    symbol_index: Mapping[str, Sequence[str]],
    caller_module: str | None,
    caller_language: str | None,
    module_lookup: Mapping[str, str],
    callable_qname_by_id: Mapping[str, str],
    import_targets: Mapping[str, set[str]],
    expanded_import_targets: Mapping[str, set[str]],
    module_ancestors: Mapping[str, set[str]],
) -> tuple[str, ...]:
    direct_candidates = list(symbol_index.get(identifier) or ())
    fallback_candidates: list[str] = []
    if not direct_candidates and "." in identifier:
        fallback_candidates = list(symbol_index.get(identifier.rsplit(".", 1)[-1]) or ())
    candidates = list(dict.fromkeys(direct_candidates or fallback_candidates))
    if len(candidates) < 2 or not caller_module:
        return ()
    allowed_modules = set(import_targets.get(caller_module, set()))
    allowed_modules.update(expanded_import_targets.get(caller_module, set()))
    allowed_modules.add(caller_module)
    allowed_modules.update(module_ancestors.get(caller_module, set()))
    narrowed: list[str] = []
    for candidate in candidates:
        candidate_module = module_lookup.get(candidate)
        if candidate_module and module_in_scope(
            candidate_module,
            allowed_modules,
            allow_descendants=caller_language == "typescript",
        ):
            narrowed.append(candidate)
    if len(narrowed) < 2:
        return ()
    if "." in identifier:
        tail_matches = []
        for candidate in narrowed:
            candidate_qname = callable_qname_by_id.get(candidate, candidate)
            if _has_structural_tail_match(
                identifier=identifier,
                candidate_qname=candidate_qname,
            ):
                tail_matches.append(candidate)
        if len(tail_matches) >= 2:
            narrowed = tail_matches
    return tuple(dict.fromkeys(narrowed))


def _has_structural_tail_match(*, identifier: str, candidate_qname: str) -> bool:
    identifier_parts = [part for part in identifier.split(".") if part]
    candidate_parts = [part for part in candidate_qname.split(".") if part]
    if len(identifier_parts) < 3 or len(candidate_parts) < 3:
        return False
    return candidate_parts[-3:] == identifier_parts[-3:]


def _resolve_post_strict_rescue_candidate(
    *,
    identifier: str,
    decision,
    symbol_index: Mapping[str, Sequence[str]],
    caller_module: str | None,
    caller_language: str | None,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
    ts_barrel_export_map: dict[str, set[str]],
    js_barrel_export_map: dict[str, set[str]],
) -> tuple[str | None, str | None]:
    if decision.accepted_candidate is not None:
        return None, None
    identifier_candidates = [identifier]
    if caller_language == "python":
        identifier_candidates.extend(_python_repeated_segment_variants(identifier))
    direct_candidates = []
    selected_identifier = identifier
    for candidate_identifier in identifier_candidates:
        direct_candidates = symbol_index.get(candidate_identifier) or []
        if direct_candidates:
            selected_identifier = candidate_identifier
            break
    fallback_candidates = []
    if not direct_candidates and "." in selected_identifier:
        fallback_candidates = symbol_index.get(
            selected_identifier.rsplit(".", 1)[-1]
        ) or []
    if caller_language == "python":
        if decision.dropped_reason not in {
            "ambiguous_no_in_scope_candidate",
            "ambiguous_multiple_in_scope_candidates",
            "unique_without_provenance",
            "no_candidates",
        }:
            return None, None
        rescue_candidate = resolve_python_export_chain_ambiguous(
            identifier=selected_identifier,
            direct_candidates=direct_candidates,
            fallback_candidates=fallback_candidates,
            caller_module=caller_module,
            callable_qname_by_id=callable_qname_by_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            module_bindings_by_name=module_bindings_by_name,
            module_file_by_name=module_file_by_name,
            simple_identifier=simple_identifier,
            module_in_scope=module_in_scope,
            best_candidate_by_module_path=best_candidate_by_module_path,
            bounded_module_reachability=bounded_module_reachability,
        )
        if rescue_candidate:
            return rescue_candidate, "export_chain_narrowed"
        return None, None
    if caller_language == "typescript":
        if decision.dropped_reason not in {
            "ambiguous_no_in_scope_candidate",
            "ambiguous_multiple_in_scope_candidates",
            "unique_without_provenance",
            "no_candidates",
        }:
            return None, None
        rescue_candidate = resolve_typescript_barrel_ambiguous(
            identifier=identifier,
            direct_candidates=direct_candidates,
            fallback_candidates=fallback_candidates,
            caller_module=caller_module,
            callable_qname_by_id=callable_qname_by_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            ts_barrel_export_map=ts_barrel_export_map,
            simple_identifier=simple_identifier,
            module_in_scope=module_in_scope,
            best_candidate_by_module_distance=best_candidate_by_module_distance,
        )
        if rescue_candidate:
            return rescue_candidate, "export_chain_narrowed"
        return None, None
    if caller_language == "javascript":
        if decision.dropped_reason not in {
            "ambiguous_no_in_scope_candidate",
            "ambiguous_multiple_in_scope_candidates",
            "unique_without_provenance",
            "no_candidates",
        }:
            return None, None
        rescue_candidate = resolve_javascript_structural_ambiguous(
            identifier=identifier,
            direct_candidates=direct_candidates,
            fallback_candidates=fallback_candidates,
            caller_module=caller_module,
            callable_qname_by_id=callable_qname_by_id,
            module_lookup=module_lookup,
            import_targets=import_targets,
            expanded_import_targets=expanded_import_targets,
            js_barrel_export_map=js_barrel_export_map,
            simple_identifier=simple_identifier,
            module_in_scope=module_in_scope,
            best_candidate_by_module_distance=best_candidate_by_module_distance,
            allow_distance_fallback=(
                decision.dropped_reason != "unique_without_provenance"
            ),
        )
        if rescue_candidate:
            return rescue_candidate, "export_chain_narrowed"
        return None, None
    return None, None


def _python_repeated_segment_variants(identifier: str) -> tuple[str, ...]:
    if "." not in identifier:
        return ()
    module_part, terminal = identifier.rsplit(".", 1)
    parts = [part for part in module_part.split(".") if part]
    if len(parts) < 2:
        return ()
    variants: list[str] = []
    for index in range(len(parts) - 1):
        if parts[index] != parts[index + 1]:
            continue
        collapsed = parts[:index] + parts[index + 1 :]
        if collapsed:
            variants.append(".".join(collapsed + [terminal]))
    return tuple(dict.fromkeys(variants))


def build_javascript_index_export_map(
    *,
    import_targets: dict[str, set[str]],
    module_bindings_by_name: dict[str, set[str]],
    module_file_by_name: dict[str, str],
) -> dict[str, set[str]]:
    return build_javascript_barrel_export_map(
        import_targets=import_targets,
        module_bindings_by_name=module_bindings_by_name,
        module_file_by_name=module_file_by_name,
        bounded_module_reachability=bounded_module_reachability,
    )


def _revalidate_rescue_candidate(
    *,
    identifier: str,
    rescue_candidate: str,
    caller_module: str | None,
    caller_language: str | None,
    callable_qname_by_id: dict[str, str],
    module_lookup: dict[str, str],
    import_targets: dict[str, set[str]],
    expanded_import_targets: dict[str, set[str]],
    caller_ancestor_modules: set[str],
):
    batch = resolve_strict_call_batch(
        [identifier],
        symbol_index={identifier: [rescue_candidate]},
        caller_module=caller_module,
        module_lookup=module_lookup,
        candidate_qualified_names=callable_qname_by_id,
        import_targets=import_targets,
        expanded_import_targets=expanded_import_targets,
        caller_ancestor_modules=caller_ancestor_modules,
        allow_descendant_scope_for_ambiguous=caller_language == "typescript",
    )
    return batch.resolutions[0].decision


def module_qname_ancestors(module_qname: str) -> set[str]:
    parts = [part for part in module_qname.split(".") if part]
    ancestors: set[str] = set()
    for end in range(len(parts) - 1, 0, -1):
        ancestors.add(".".join(parts[:end]))
    return ancestors


def module_in_scope(
    candidate_module: str,
    allowed_modules: set[str],
    *,
    allow_descendants: bool,
) -> bool:
    for allowed in allowed_modules:
        if candidate_module == allowed:
            return True
        if allow_descendants and candidate_module.startswith(f"{allowed}."):
            return True
    return False


def best_candidate_by_module_path(
    candidates: Sequence[str],
    module_lookup: dict[str, str],
    callable_qname_by_id: dict[str, str],
) -> str:
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            len((module_lookup.get(candidate) or "").split(".")),
            module_lookup.get(candidate) or "",
            callable_qname_by_id.get(candidate) or "",
            candidate,
        ),
    )
    return ranked[0]


def bounded_module_reachability(
    import_targets: dict[str, set[str]],
    *,
    start: str,
    max_depth: int,
) -> set[str]:
    if max_depth <= 0:
        return set()
    reached: set[str] = set()
    frontier = {start}
    visited = {start}
    for _ in range(max_depth):
        next_frontier: set[str] = set()
        for module in frontier:
            for target in import_targets.get(module, set()):
                if target in visited:
                    continue
                visited.add(target)
                reached.add(target)
                next_frontier.add(target)
        if not next_frontier:
            break
        frontier = next_frontier
    return reached


def best_candidate_by_module_distance(
    candidates: Sequence[str],
    *,
    caller_module: str,
    module_lookup: dict[str, str],
    callable_qname_by_id: dict[str, str],
    import_targets: dict[str, set[str]],
) -> str:
    ranked = sorted(
        candidates,
        key=lambda candidate: (
            module_distance(
                caller_module,
                module_lookup.get(candidate) or "",
                import_targets=import_targets,
                max_depth=6,
            ),
            len((module_lookup.get(candidate) or "").split(".")),
            callable_qname_by_id.get(candidate) or "",
            candidate,
        ),
    )
    return ranked[0]


def module_distance(
    src_module: str,
    dst_module: str,
    *,
    import_targets: dict[str, set[str]],
    max_depth: int,
) -> int:
    if not dst_module:
        return max_depth + 100
    if src_module == dst_module:
        return 0
    frontier = {src_module}
    visited = {src_module}
    for depth in range(1, max_depth + 1):
        next_frontier: set[str] = set()
        for module in frontier:
            for target in import_targets.get(module, set()):
                if target in visited:
                    continue
                if dst_module == target or dst_module.startswith(f"{target}."):
                    return depth
                visited.add(target)
                next_frontier.add(target)
        frontier = next_frontier
        if not frontier:
            break
    return max_depth + 100


def simple_identifier(qualified_name: str) -> str | None:
    if not qualified_name:
        return None
    parts = qualified_name.rsplit(".", 1)
    return parts[-1] if parts else qualified_name
