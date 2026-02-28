# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass

from sciona.code_analysis.contracts import select_strict_call_candidate


@dataclass(frozen=True)
class ContractCallCandidates:
    identifier: str
    direct_candidates: list[str]
    fallback_candidates: list[str]


@dataclass(frozen=True)
class ContractCallResolution:
    callee_qname: str | None
    accepted_provenance: str | None
    dropped_reason: str | None
    candidate_count: int


def build_call_resolution_context_from_nodes(nodes: list[dict]) -> dict:
    symbol_index: dict[str, set[str]] = {}
    module_lookup: dict[str, str] = {}
    for entry in nodes:
        node_type = entry.get("node_type") or entry.get("node_kind")
        if node_type not in {"function", "method"}:
            continue
        qname = entry.get("qualified_name")
        if not qname:
            continue
        identifier = qname.split(".")[-1]
        symbol_index.setdefault(identifier, set()).add(qname)
        module_name = entry.get("module_qualified_name")
        if not module_name:
            parts = qname.split(".")
            module_name = ".".join(parts[:-1]) if len(parts) > 1 else qname
        module_lookup[qname] = module_name
    return {
        "symbol_index": {k: sorted(v) for k, v in symbol_index.items()},
        "module_lookup": module_lookup,
    }


def _qualifier_from_text(edge) -> str | None:
    text = (getattr(edge, "callee_text", None) or "").strip()
    if not text:
        text = (edge.callee_qname or "").strip()
    if not text:
        return None
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    if "." not in text:
        return None
    return text.rsplit(".", 1)[0].strip() or None


def _candidate_identifiers(edge) -> list[str]:
    candidates: list[str] = []
    for raw in [edge.callee_qname, edge.callee]:
        if not raw:
            continue
        value = raw.strip()
        if not value:
            continue
        candidates.append(value.split(".")[-1] if "." in value else value)
    text = (getattr(edge, "callee_text", None) or "").strip()
    if text:
        head = text.split("(", 1)[0].strip()
        if head:
            candidates.append(head.split(".")[-1].strip())
    return _dedupe(candidates)


def _by_module(candidates: list[str], module_lookup: dict[str, str], module: str) -> list[str]:
    return [candidate for candidate in candidates if module_lookup.get(candidate) == module]


def _by_prefix(candidates: list[str], prefix: str) -> list[str]:
    return [candidate for candidate in candidates if candidate.startswith(prefix)]


def _qualifier_leaf(edge) -> str | None:
    qualifier = _qualifier_from_text(edge)
    if not qualifier:
        return None
    return qualifier.split(".")[-1]


def _qualifier_tokens(edge) -> list[str]:
    qualifier = _qualifier_from_text(edge)
    if not qualifier:
        return []
    return [token for token in qualifier.split(".") if token]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def build_contract_call_candidates(
    edge,
    caller_qname: str,
    caller_module: str,
    call_resolution: dict,
) -> ContractCallCandidates:
    symbol_index: dict[str, list[str]] = call_resolution.get("symbol_index", {})
    module_lookup: dict[str, str] = call_resolution.get("module_lookup", {})

    identifiers = _candidate_identifiers(edge)
    identifier = identifiers[0] if identifiers else ""

    direct_candidates: list[str] = []
    if edge.callee_qname and edge.callee_qname in module_lookup:
        direct_candidates = [edge.callee_qname]

    pooled: list[str] = []
    if identifier:
        pooled.extend(symbol_index.get(identifier) or [])
    for alternate in identifiers[1:]:
        pooled.extend(symbol_index.get(alternate) or [])

    fallback_candidates = _dedupe(pooled)
    return ContractCallCandidates(
        identifier=identifier,
        direct_candidates=direct_candidates,
        fallback_candidates=fallback_candidates,
    )


def resolve_call_in_contract_details(
    edge,
    caller_qname: str,
    caller_module: str,
    call_resolution: dict,
) -> ContractCallResolution:
    candidates = build_contract_call_candidates(edge, caller_qname, caller_module, call_resolution)
    decision = select_strict_call_candidate(
        identifier=candidates.identifier,
        direct_candidates=candidates.direct_candidates,
        fallback_candidates=candidates.fallback_candidates,
        caller_module=caller_module,
        module_lookup=call_resolution.get("module_lookup", {}),
        import_targets=call_resolution.get("import_targets", {}),
    )
    return ContractCallResolution(
        callee_qname=decision.accepted_candidate,
        accepted_provenance=decision.accepted_provenance,
        dropped_reason=decision.dropped_reason,
        candidate_count=decision.candidate_count,
    )


def resolve_call_in_contract(
    edge,
    caller_qname: str,
    caller_module: str,
    call_resolution: dict,
) -> str | None:
    return resolve_call_in_contract_details(
        edge=edge,
        caller_qname=caller_qname,
        caller_module=caller_module,
        call_resolution=call_resolution,
    ).callee_qname


def call_in_contract(
    edge,
    caller_qname: str,
    caller_module: str,
    call_resolution: dict,
) -> bool:
    return (
        resolve_call_in_contract(edge, caller_qname, caller_module, call_resolution)
        is not None
    )
