#!/usr/bin/env python3
"""Reducer quality evaluator with reducer-specific invocation and validation.

This tool is designed to be reusable across repositories that have SCIONA data.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
import random
import re
import sqlite3
import statistics
import tempfile
import shutil
import time
from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, TypedDict

import yaml
from sciona.data_storage.connections import artifact as artifact_db
from sciona.data_storage.connections import artifact_readonly as artifact_db_readonly
from sciona.data_storage.connections import core as core_db
from sciona.data_storage.connections import core_readonly as core_db_readonly
from sciona.pipelines import reducers as reducers_pipeline
from sciona.pipelines.policy import snapshot as snapshot_policy
from sciona.reducers.helpers.context import use_artifact_connection
from sciona.reducers.registry import get_reducers, load_reducer
from sciona.runtime.paths import get_artifact_db_path, get_db_path
from sciona.runtime.text import canonical_span_bytes, canonical_span_text

try:
    from tree_sitter_languages import get_parser as ts_get_parser
except Exception:  # pragma: no cover
    ts_get_parser = None


SOURCE_REDUCERS = {"concatenated_source", "callable_source"}
SUMMARY_REDUCERS = {
    "class_call_graph_summary",
    "class_overview",
    "hotspot_summary",
    "module_call_graph_summary",
    "module_overview",
}
IDENT_NODE_TYPES = {"identifier", "type_identifier", "property_identifier"}
COMPOSITE_IDENT_NODE_TYPES = {"dotted_name", "scoped_identifier"}
TREE_SITTER_LANG_ALIASES = {
    "python": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "tsx": "tsx",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
}
_TS_PARSER_CACHE: dict[str, Any] = {}
MAX_HASH_DIAGNOSTICS = 50
HASH_SNIPPET_LIMIT = 400
MAX_APPENDIX_DIAGNOSTICS = 100
SCRIPT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = SCRIPT_DIR.parent / "reports"

DEFAULT_THRESHOLDS = {
    "blind_error_rate_max": 0.01,
    "content_hash_match_min": 0.98,
    "hash_diagnostics_max": 50,
    "empty_match_rate_max": 0.3,
    "blind_error_rate_increase": 0.01,
    "content_hash_match_drop": 0.02,
    "hash_diagnostics_increase": 25,
    "empty_match_rate_increase": 0.05,
    "identifier_overlap_drop": 0.1,
}

DEFAULT_CONTRACT_DEFAULTS = {
    "reducer_type": "structural",
    "overlap_policy": {"enabled": True},
    "structural_accuracy_policy": {"enabled": True},
    "unknown_policy": {
        "enabled": True,
        "penalize_out_of_scope": False,
        "penalize_out_of_sample": False,
        "penalize_unresolved_in_scope": True,
        "penalize_resolution_failure": True,
    },
    "allow_empty": [],
    "min_items": {},
}


@dataclass(frozen=True)
class Entity:
    structural_id: str
    qualified_name: str
    kind: str
    language: str
    file_path: str
    start_line: int | None
    end_line: int | None


@dataclass(frozen=True)
class InvocationSpec:
    entity: Entity | None
    kwargs: dict[str, Any]
    label: str
    is_negative: bool = False


@dataclass
class EvalContext:
    ts_failures: int = 0
    ts_ignored_files: int = 0


class BlindSummary(TypedDict, total=False):
    id_resolution_rate: float
    file_span_valid_rate: float
    count_consistency_rate: float
    line_span_hash_match_rate: float
    content_hash_match_rate: float
    blind_error_rate: float
    failures: list[str]
    hash_diagnostics: list[dict[str, Any]]
    hash_diagnostics_total: int


class ContractValidation(TypedDict, total=False):
    missing_required_paths: list[str]
    unknown_payload_keys: list[str]
    type_mismatches: list[str]
    invariant_failures: list[str]


class ReducerMetrics(TypedDict, total=False):
    samples: int
    invocations: int
    inference: dict[str, Any]
    reducer_type: str
    structural_variance: float
    semantic_variance: float
    token_length_variation_cv: float
    unknown_id_qname_rate: float | None
    unknown_id_qname_out_of_scope_rate: float | None
    unknown_id_qname_out_of_sample_rate: float | None
    unknown_id_qname_unresolved_in_scope_rate: float | None
    unknown_id_qname_resolution_failure_rate: float | None
    omission_rate: float
    structural_accuracy: float | None
    identifier_overlap: float | None
    length_stability: float
    ordering_instability_rate: float
    determinism_score: float
    schema_compliance_score: float
    coverage_score: float
    empty_match_rate: float | None
    error_rate: float
    latency_ms_avg: float | None
    latency_ms_p95: float | None
    latency_ms_max: float | None
    cross_run_structural_diff: float
    forbidden_fields_present: int
    blind: BlindSummary
    negative_probes: list[dict[str, Any]]
    db_checks: dict[str, Any]
    source_assessment: dict[str, Any]
    contract: dict[str, Any]
    contract_validation: ContractValidation
    errors_total: int
    errors_sample: list[str]


@dataclass(frozen=True)
class SamplingData:
    sampled: list[Entity]
    sampled_ids: set[str]
    sampled_qnames: set[str]
    direct_terms: dict[str, set[str]]
    direct_method_by_entity: dict[str, str]
    query_terms: dict[str, str]
    population_by_language: dict[str, int]
    population_by_kind: dict[str, int]


@dataclass(frozen=True)
class GroundTruth:
    gt_qnames: set[str]
    gt_module_qnames: set[str]
    gt_ids: set[str]
    gt_edges: set[tuple[str, str]]
    art_nodes: set[str]
    art_edges: set[tuple[str, str]]


@dataclass(frozen=True)
class EvalOutput:
    reducer_results: dict[str, ReducerMetrics]
    coherence_store: dict[str, dict[str, dict[str, Any]]]
    blind_rates_by_language: dict[str, list[BlindSummary]]
    blind_rates_by_kind: dict[str, list[BlindSummary]]
    hash_appendix: list[dict[str, Any]]
    calls_used: int
    invocations_total: int
    invocation_errors: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate SCIONA reducers systematically.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Root of the repository to evaluate (can be external).",
    )
    parser.add_argument("--nodes", type=int, default=12, help="Total entities to sample.")
    parser.add_argument("--runs", type=int, default=10, help="Runs per invocation.")
    parser.add_argument("--seed", type=int, default=20260212)
    parser.add_argument(
        "--reducers",
        type=str,
        default="",
        help="Comma-separated list of reducer ids to evaluate (default: all).",
    )
    parser.add_argument("--mode", choices=["full"], default="full")
    parser.add_argument(
        "--db-readonly",
        action="store_true",
        help="Open SCIONA DBs in read-only mode (useful for shared or locked repos).",
    )
    parser.add_argument(
        "--contracts",
        type=Path,
        default=SCRIPT_DIR / "reducer_contracts.yaml",
        help="Path to reducer contracts (defaults to this script's directory).",
    )
    parser.add_argument(
        "--baseline-json",
        type=Path,
        default=None,
        help="Optional baseline JSON report to diff against for regressions.",
    )
    parser.add_argument(
        "--regression-thresholds",
        type=Path,
        default=None,
        help="Optional YAML/JSON file with regression thresholds.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPORTS_DIR / "reducer_quality_evaluation.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=REPORTS_DIR / "reducer_quality_evaluation.md",
    )
    return parser.parse_args()


def _use_readonly_db(db_path: Path, force_readonly: bool) -> bool:
    if force_readonly:
        return True
    parent = db_path.parent
    if not parent.exists():
        return False
    return not os.access(parent, os.W_OK)


def _open_core_db(
    db_path: Path, *, repo_root: Path, read_only: bool
):
    if read_only:
        return core_db_readonly(db_path, repo_root=repo_root)
    return core_db(db_path, repo_root=repo_root)


def _open_artifact_db(
    db_path: Path, *, repo_root: Path, read_only: bool
):
    if read_only:
        return artifact_db_readonly(db_path, repo_root=repo_root)
    return artifact_db(db_path, repo_root=repo_root)


def _copy_db_to_tmp(db_path: Path, *, label: str) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"sciona_{label}_"))
    dest = temp_dir / db_path.name
    shutil.copy2(db_path, dest)
    return dest


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_\\.]*", text))


def _qname_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"\b[a-zA-Z_][\w]*(?:\.[A-Za-z_][\w]*){1,}\b", text))
    return {t for t in tokens if "." in t}


def _structural_id_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b[0-9a-f]{40}\b", text))


def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return 1.0 if not union else len(a & b) / len(union)


def _safe_mean(values: list[float], default: float | None = None) -> float | None:
    return (sum(values) / len(values)) if values else default


def _safe_ratio(numerator: float, denominator: float, default: float = 0.0) -> float:
    return (numerator / denominator) if denominator else default


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _fmt_metric(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value}"


def _normalize_payload_text(text: str, echo_fields: Iterable[str] | None = None) -> str:
    body = text.strip()
    if body.startswith("```json"):
        body = body[len("```json") :].strip()
    if body.endswith("```"):
        body = body[:-3].strip()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if echo_fields:
        payload = _prune_echo_fields(payload, set(echo_fields))
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _maybe_json(text: str) -> dict[str, Any] | None:
    body = text.strip()
    if body.startswith("```json"):
        body = body[len("```json") :].strip()
    if body.endswith("```"):
        body = body[:-3].strip()
    try:
        val = json.loads(body)
    except json.JSONDecodeError:
        return None
    return val if isinstance(val, dict) else None


def _prune_echo_fields(payload: Any, echo_fields: set[str]) -> Any:
    if isinstance(payload, dict):
        return {
            key: _prune_echo_fields(value, echo_fields)
            for key, value in payload.items()
            if key not in echo_fields
        }
    if isinstance(payload, list):
        return [_prune_echo_fields(item, echo_fields) for item in payload]
    return payload


def _payload_text_for_checks(text: str, echo_fields: Iterable[str] | None) -> str:
    payload = _maybe_json(text)
    if payload is None or not echo_fields:
        return text
    pruned = _prune_echo_fields(payload, set(echo_fields))
    return json.dumps(pruned, sort_keys=True, separators=(",", ":"))


def _drop_content_hash_fields(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _drop_content_hash_fields(value)
            for key, value in payload.items()
            if not (key == "content_hash" or key.endswith("_content_hash"))
        }
    if isinstance(payload, list):
        return [_drop_content_hash_fields(item) for item in payload]
    return payload


def _collect_evidence_identifiers(payload: Any) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    qnames: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, dict) or isinstance(value, list):
                child_ids, child_q = _collect_evidence_identifiers(value)
                ids.extend(child_ids)
                qnames.extend(child_q)
                continue
            if not isinstance(value, str):
                continue
            if key.endswith("_id") or key.endswith("_structural_id") or key == "structural_id":
                if re.fullmatch(r"[0-9a-f]{40}", value):
                    ids.append(value)
            if key.endswith("qualified_name"):
                if re.fullmatch(r"[0-9a-f]{40}", value):
                    ids.append(value)
                else:
                    qnames.append(value)
    elif isinstance(payload, list):
        for item in payload:
            child_ids, child_q = _collect_evidence_identifiers(item)
            ids.extend(child_ids)
            qnames.extend(child_q)
    return ids, qnames


def _qname_matches(value: str, gt_qnames: set[str], *, allow_suffix: bool = False) -> bool:
    if value in gt_qnames:
        return True
    if allow_suffix:
        suffix = f".{value.lstrip('.')}"
        return any(name.endswith(suffix) for name in gt_qnames)
    return False


def _qname_in_sample(value: str, sampled_qnames: set[str], *, allow_suffix: bool = False) -> bool:
    if value in sampled_qnames:
        return True
    if allow_suffix:
        suffix = f".{value.lstrip('.')}"
        return any(name.endswith(suffix) for name in sampled_qnames)
    return False


def _qname_in_scope(
    value: str, module_qnames: set[str], *, allow_suffix: bool = False
) -> bool:
    if value in module_qnames:
        return True
    if "." in value:
        return any(
            value.startswith(f"{module}.") for module in module_qnames
        )
    if allow_suffix:
        suffix = f".{value.lstrip('.')}"
        return any(module.endswith(suffix) for module in module_qnames)
    return False


def _semantic_tokens_from_payload(payload: Any, stop_tokens: set[str] | None = None) -> set[str]:
    tokens: set[str] = set()
    if stop_tokens is None:
        stop_tokens = set()

    def _visit(obj: Any) -> None:
        if isinstance(obj, dict):
            for value in obj.values():
                _visit(value)
        elif isinstance(obj, list):
            for item in obj:
                _visit(item)
        elif isinstance(obj, str):
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", obj):
                if token not in stop_tokens:
                    tokens.add(token)

    _visit(payload)
    return tokens


def _load_entities(repo_root: Path, db_path: Path, snapshot_id: str) -> list[Entity]:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        """
        SELECT
            ni.structural_id,
            ni.qualified_name,
            sn.node_type AS kind,
            sn.language,
            ni.file_path,
            ni.start_line,
            ni.end_line
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ('module', 'class', 'function', 'method')
        """,
        (snapshot_id,),
    ).fetchall()
    db.close()

    entities: list[Entity] = []
    for row in rows:
        file_path = row["file_path"] or ""
        full_path = repo_root / file_path
        if not file_path or not full_path.exists() or not full_path.is_file():
            continue
        entities.append(
            Entity(
                structural_id=row["structural_id"],
                qualified_name=row["qualified_name"],
                kind=row["kind"],
                language=row["language"],
                file_path=file_path,
                start_line=row["start_line"],
                end_line=row["end_line"],
            )
        )
    return entities


def _sample_balanced(entities: list[Entity], total_nodes: int, seed: int) -> list[Entity]:
    if total_nodes <= 0:
        return []
    by_lang: dict[str, list[Entity]] = defaultdict(list)
    for e in entities:
        by_lang[e.language].append(e)
    languages = sorted(by_lang)
    if not languages:
        return []

    rng = random.Random(seed)
    quotas = {lang: total_nodes // len(languages) for lang in languages}
    for i in range(total_nodes % len(languages)):
        quotas[languages[i]] += 1

    sampled: list[Entity] = []
    used_ids: set[str] = set()
    for lang in languages:
        pool = by_lang[lang]
        by_kind = {
            "module": [e for e in pool if e.kind == "module"],
            "class": [e for e in pool if e.kind == "class"],
            "callable": [e for e in pool if e.kind in {"function", "method"}],
        }
        order = ["module", "class", "callable"]
        quota = quotas[lang]
        idx = 0
        while quota > 0 and any(by_kind[k] for k in order):
            kind = order[idx % len(order)]
            idx += 1
            if not by_kind[kind]:
                continue
            choice = rng.choice(by_kind[kind])
            by_kind[kind] = [e for e in by_kind[kind] if e.structural_id != choice.structural_id]
            if choice.structural_id in used_ids:
                continue
            sampled.append(choice)
            used_ids.add(choice.structural_id)
            quota -= 1

    if len(sampled) < total_nodes:
        rest = [e for e in entities if e.structural_id not in used_ids]
        rng.shuffle(rest)
        sampled.extend(rest[: total_nodes - len(sampled)])
    return sampled[:total_nodes]


def _ast_terms(repo_root: Path, entity: Entity) -> set[str]:
    terms = {entity.qualified_name.split(".")[-1]}
    path = repo_root / entity.file_path
    if entity.language != "python":
        return terms

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return terms

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                terms.add(alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom) and node.module:
            terms.add(node.module.split(".")[-1])

    target = entity.qualified_name.split(".")[-1]
    if entity.kind == "class":
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == target:
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        terms.add(base.id)
                    elif isinstance(base, ast.Attribute):
                        terms.add(base.attr)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        terms.add(child.name)
                break
    elif entity.kind in {"function", "method"}:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
                for arg in node.args.args:
                    terms.add(arg.arg)
                break

    return {t for t in terms if t}


def _node_text(src: bytes, node: Any) -> str:
    chunk = src[node.start_byte : node.end_byte]
    return chunk.decode("utf-8", errors="ignore")


def _extract_tree_sitter_terms(
    repo_root: Path, entity: Entity, ctx: EvalContext
) -> set[str]:
    if ts_get_parser is None:
        return set()
    lang_key = TREE_SITTER_LANG_ALIASES.get(entity.language.lower())
    if not lang_key:
        return set()

    parser = _TS_PARSER_CACHE.get(lang_key)
    if parser is None and lang_key not in _TS_PARSER_CACHE:
        try:
            parser = ts_get_parser(lang_key)
        except Exception:
            parser = None
        _TS_PARSER_CACHE[lang_key] = parser
    if parser is None:
        return set()

    path = repo_root / entity.file_path
    try:
        src = path.read_bytes()
    except Exception:
        ctx.ts_ignored_files += 1
        return set()

    try:
        tree = parser.parse(src)
    except Exception:
        ctx.ts_failures += 1
        return set()

    terms: set[str] = set()
    target_start = entity.start_line or 1
    target_end = entity.end_line or 10**9

    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        row = node.start_point[0] + 1
        if entity.kind != "module" and (row < target_start or row > target_end):
            stack.extend(getattr(node, "children", []))
            continue

        ntype = node.type
        if ntype in IDENT_NODE_TYPES:
            txt = _node_text(src, node).strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", txt):
                terms.add(txt)
        elif ntype in COMPOSITE_IDENT_NODE_TYPES:
            txt = _node_text(src, node).strip()
            parts = re.split(r"[.:]+", txt)
            for part in parts:
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
                    terms.add(part)

        stack.extend(getattr(node, "children", []))
    return terms


def _code_terms(repo_root: Path, entity: Entity, ctx: EvalContext) -> tuple[set[str], str]:
    ts_terms = _extract_tree_sitter_terms(repo_root, entity, ctx)
    if ts_terms:
        ts_terms.add(entity.qualified_name.split(".")[-1])
        return ts_terms, "tree_sitter"
    return _ast_terms(repo_root, entity), "ast_fallback"


def _load_contracts(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def _contract_requirements(contracts: dict[str, dict[str, Any]], reducer_id: str) -> dict[str, Any]:
    defaults = contracts.get("_defaults", {})
    entry = contracts.get(reducer_id, {})
    merged = {**DEFAULT_CONTRACT_DEFAULTS, **defaults, **entry}
    return {
        "required_fields": merged.get("required_fields", []),
        "optional_fields": merged.get("optional_fields", []),
        "forbidden_fields": merged.get("forbidden_fields", []),
        "required_paths": merged.get("required_paths", []),
        "scope": merged.get("scope"),
        "invoke": merged.get("invoke", {}),
        "types": merged.get("types", {}),
        "invariants": merged.get("invariants", []),
        "echo_fields": merged.get("echo_fields", []),
        "evidence_fields": merged.get("evidence_fields", []),
        "qname_allow_suffix": bool(merged.get("qname_allow_suffix", False)),
        "reducer_type": merged.get("reducer_type", "structural"),
        "overlap_policy": merged.get("overlap_policy", {}),
        "structural_accuracy_policy": merged.get("structural_accuracy_policy", {}),
        "unknown_policy": merged.get("unknown_policy", {}),
        "allow_empty": merged.get("allow_empty", []),
        "min_items": merged.get("min_items", {}),
    }


def _policy_enabled(policy: Any, default: bool | None = True) -> bool | None:
    if isinstance(policy, dict):
        if "enabled" in policy:
            return bool(policy["enabled"])
        return default
    if isinstance(policy, bool):
        return policy
    return default


def _reducer_type(contract: dict[str, Any]) -> str:
    return str(contract.get("reducer_type") or "structural")


def _structural_accuracy_enabled(contract: dict[str, Any]) -> bool:
    policy = contract.get("structural_accuracy_policy", {})
    enabled = _policy_enabled(policy, default=None)
    if enabled is not None:
        return enabled
    reducer_type = _reducer_type(contract)
    return reducer_type == "structural"


def _overlap_enabled(contract: dict[str, Any], reducer_id: str) -> bool:
    policy = contract.get("overlap_policy", {})
    enabled = _policy_enabled(policy, default=None)
    if enabled is not None:
        return enabled
    reducer_type = _reducer_type(contract)
    if reducer_type:
        return reducer_type in {"structural", "projection", "query"}
    return reducer_id not in SUMMARY_REDUCERS


def _unknown_checks_enabled(contract: dict[str, Any], reducer_id: str) -> bool:
    if reducer_id in SOURCE_REDUCERS:
        return False
    policy = contract.get("unknown_policy", {})
    return _policy_enabled(policy, default=True)


def _unknown_penalty(
    policy: dict[str, Any],
    *,
    out_of_scope: int,
    out_of_sample: int,
    unresolved_in_scope: int,
    resolution_failure: int,
) -> int:
    total = 0
    if policy.get("penalize_out_of_scope", False):
        total += out_of_scope
    if policy.get("penalize_out_of_sample", False):
        total += out_of_sample
    if policy.get("penalize_unresolved_in_scope", True):
        total += unresolved_in_scope
    if policy.get("penalize_resolution_failure", True):
        total += resolution_failure
    return total


def _schema_compliance(
    payload: dict[str, Any] | None, contract: dict[str, Any]
) -> tuple[int, int, int, int, list[str], int, int, list[str], int, int, list[str]]:
    required = contract.get("required_fields", [])
    required_paths = contract.get("required_paths", [])
    forbidden = contract.get("forbidden_fields", [])
    type_rules = contract.get("types", {})
    invariants = contract.get("invariants", [])
    allow_empty = contract.get("allow_empty", [])
    min_items = contract.get("min_items", {})
    if payload is None:
        list_missing = (
            [f"allow_empty:{field}" for field in allow_empty]
            + [f"min_items:{field}:{value}" for field, value in (min_items or {}).items()]
        )
        return (
            0,
            len(required),
            0,
            len(required_paths),
            list(required_paths),
            0,
            len(type_rules),
            list(type_rules.keys()),
            0,
            len(invariants) + len(list_missing),
            [str(item) for item in invariants] + list_missing,
        )
    present_required = sum(1 for key in required if key in payload)
    forbidden_hits = sum(1 for key in forbidden if key in payload)
    present_paths, missing_paths = _validate_paths(payload, required_paths)
    type_ok, type_total, type_missing = _type_check(payload, type_rules)
    invariant_ok, invariant_total, invariant_missing = _invariant_check(payload, invariants)
    list_ok, list_total, list_missing = _list_policy_check(payload, allow_empty, min_items)
    return (
        present_required,
        len(required),
        forbidden_hits,
        len(required_paths),
        missing_paths,
        type_ok,
        type_total,
        type_missing,
        invariant_ok + list_ok,
        invariant_total + list_total,
        invariant_missing + list_missing,
    )


def _normalize_report_path(repo_root: Path, value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        try:
            return candidate.relative_to(repo_root).as_posix()
        except Exception:
            return (Path("repo_root") / "external" / candidate.name).as_posix()
    return candidate.as_posix()


def _blind_checks(
    payload: dict[str, Any] | None,
    gt_ids: set[str],
    repo_root: Path,
    *,
    reducer_id: str | None = None,
    entity: Entity | None = None,
) -> BlindSummary:
    if payload is None:
        return {
            "id_resolution_rate": 0.0,
            "file_span_valid_rate": 0.0,
            "count_consistency_rate": 0.0,
            "line_span_hash_match_rate": 0.0,
            "content_hash_match_rate": 0.0,
            "blind_error_rate": 1.0,
            "failures": ["payload_not_json"],
            "hash_diagnostics": [],
        }

    ids = _collect_ids(payload)
    id_hits = sum(1 for value in ids if value in gt_ids)
    id_rate = (id_hits / len(ids)) if ids else 1.0

    span_records = _collect_span_records(payload)
    span_hits = 0
    for record in span_records:
        file_path = record.get("file_path")
        span = record.get("line_span")
        if not file_path:
            continue
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = repo_root / full_path
        if not full_path.exists() or not full_path.is_file():
            continue
        try:
            lines = full_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        if not span or len(span) != 2:
            continue
        start, end = span
        if isinstance(start, int) and isinstance(end, int) and 1 <= start <= end <= max(1, len(lines)):
            span_hits += 1
    span_rate = (span_hits / len(span_records)) if span_records else 1.0

    hash_hits = 0
    hash_total = 0
    span_hash_hits = 0
    span_hash_total = 0
    hash_diagnostics: list[dict[str, Any]] = []
    hash_diagnostics_total = 0
    for record in span_records:
        content_hash = record.get("content_hash")
        file_path = record.get("file_path")
        span = record.get("line_span")
        start_byte = record.get("start_byte")
        end_byte = record.get("end_byte")
        if not file_path or not span or len(span) != 2:
            continue
        snippet = _extract_span_text(repo_root, file_path, span)
        if snippet is None:
            continue
        if isinstance(start_byte, int) and isinstance(end_byte, int):
            snippet_bytes = _extract_span_bytes(repo_root, file_path, start_byte, end_byte)
            hash_source = "byte_span"
        else:
            snippet_bytes = _extract_line_span_bytes(repo_root, file_path, span)
            hash_source = "line_span"
        if snippet_bytes is None:
            continue
        if isinstance(content_hash, str):
            hash_total += 1
            matched = _content_hash_matches_bytes(snippet_bytes, content_hash)
            if matched:
                hash_hits += 1
            elif len(hash_diagnostics) < MAX_HASH_DIAGNOSTICS:
                hash_diagnostics_total += 1
                report_file_path = _normalize_report_path(repo_root, str(file_path))
                candidates = _content_hash_candidates_bytes(snippet_bytes)
                hash_diagnostics.append(
                    {
                        "reducer_id": reducer_id,
                        "entity_id": entity.structural_id if entity else None,
                        "entity_qname": entity.qualified_name if entity else None,
                        "file_path": report_file_path,
                        "line_span": span,
                        "byte_span": [start_byte, end_byte]
                        if isinstance(start_byte, int) and isinstance(end_byte, int)
                        else None,
                        "content_hash": content_hash,
                        "line_span_hash": record.get("line_span_hash"),
                        "snippet": snippet,
                        "snippet_preview": _snippet_preview(snippet),
                        "snippet_length": len(snippet),
                        "hash_source": hash_source,
                        "candidates": [
                            {
                                "sha1": hashlib.sha1(candidate).hexdigest(),
                                "preview": _snippet_preview_bytes(candidate),
                                "length": len(candidate),
                            }
                            for candidate in candidates
                        ],
                    }
                )
            elif not matched:
                hash_diagnostics_total += 1
        line_span_hash = record.get("line_span_hash")
        if isinstance(line_span_hash, str):
            span_hash_total += 1
            if _line_span_hash_matches(snippet, line_span_hash):
                span_hash_hits += 1
    hash_rate = (hash_hits / hash_total) if hash_total else 1.0
    span_hash_rate = (span_hash_hits / span_hash_total) if span_hash_total else 1.0

    count_pairs = _collect_count_pairs(payload)
    count_hits = sum(1 for count, actual in count_pairs if count == actual)
    count_rate = (count_hits / len(count_pairs)) if count_pairs else 1.0

    failures = []
    if id_rate < 1.0:
        failures.append("id_resolution")
    if span_rate < 1.0:
        failures.append("file_span")
    if count_rate < 1.0:
        failures.append("count_mismatch")
    if span_hash_rate < 1.0:
        failures.append("line_span_hash")
    if hash_rate < 1.0:
        failures.append("content_hash")

    blind_error_rate = 1.0 - ((id_rate + span_rate + count_rate + span_hash_rate + hash_rate) / 5.0)
    return {
        "id_resolution_rate": round(id_rate, 4),
        "file_span_valid_rate": round(span_rate, 4),
        "count_consistency_rate": round(count_rate, 4),
        "line_span_hash_match_rate": round(span_hash_rate, 4),
        "content_hash_match_rate": round(hash_rate, 4),
        "blind_error_rate": round(blind_error_rate, 4),
        "failures": failures,
        "hash_diagnostics": hash_diagnostics,
        "hash_diagnostics_total": hash_diagnostics_total,
    }


def _aggregate_blind(entries: list[dict[str, Any]]) -> BlindSummary:
    if not entries:
        return {
            "id_resolution_rate": 1.0,
            "file_span_valid_rate": 1.0,
            "count_consistency_rate": 1.0,
            "line_span_hash_match_rate": 1.0,
            "content_hash_match_rate": 1.0,
            "blind_error_rate": 0.0,
            "failures": [],
            "hash_diagnostics": [],
            "hash_diagnostics_total": 0,
        }
    def _avg(key: str) -> float:
        return _safe_mean([item.get(key, 0.0) for item in entries], default=0.0) or 0.0
    failures = sorted({f for item in entries for f in item.get("failures", [])})
    diagnostics: list[dict[str, Any]] = []
    diagnostics_total = 0
    for item in entries:
        diagnostics_total += int(item.get("hash_diagnostics_total", 0) or 0)
        for diag in item.get("hash_diagnostics", []):
            if len(diagnostics) >= MAX_HASH_DIAGNOSTICS:
                break
            diagnostics.append(diag)
        if len(diagnostics) >= MAX_HASH_DIAGNOSTICS:
            break
    return {
        "id_resolution_rate": round(_avg("id_resolution_rate"), 4),
        "file_span_valid_rate": round(_avg("file_span_valid_rate"), 4),
        "count_consistency_rate": round(_avg("count_consistency_rate"), 4),
        "line_span_hash_match_rate": round(_avg("line_span_hash_match_rate"), 4),
        "content_hash_match_rate": round(_avg("content_hash_match_rate"), 4),
        "blind_error_rate": round(_avg("blind_error_rate"), 4),
        "failures": failures,
        "hash_diagnostics": diagnostics,
        "hash_diagnostics_total": diagnostics_total,
    }


def _order_invariant_dump(payload: Any) -> str:
    def _normalize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {key: _normalize(value) for key, value in sorted(obj.items())}
        if isinstance(obj, list):
            normalized = [_normalize(item) for item in obj]
            normalized.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
            return normalized
        return obj

    return json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"))


def _collect_ids(payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key, value in _walk_payload(payload):
        if not isinstance(value, str):
            continue
        if key.endswith("_id") or key.endswith("_structural_id") or key == "structural_id":
            if re.fullmatch(r"[0-9a-f]{40}", value):
                ids.append(value)
    return ids


def _collect_span_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    def _visit(obj: Any) -> None:
        if isinstance(obj, dict):
            if "file_path" in obj and "line_span" in obj:
                records.append(
                    {
                        "file_path": obj.get("file_path"),
                        "line_span": obj.get("line_span"),
                        "line_span_hash": obj.get("line_span_hash"),
                        "content_hash": obj.get("content_hash"),
                        "start_byte": obj.get("start_byte"),
                        "end_byte": obj.get("end_byte"),
                    }
                )
            for value in obj.values():
                _visit(value)
        elif isinstance(obj, list):
            for item in obj:
                _visit(item)
    _visit(payload)
    return records


def _collect_count_pairs(payload: dict[str, Any]) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    def _visit(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.endswith("_count") and isinstance(value, int):
                    base = key[:-6]
                    sibling = obj.get(base)
                    if isinstance(sibling, list):
                        pairs.append((value, len(sibling)))
                _visit(value)
        elif isinstance(obj, list):
            for item in obj:
                _visit(item)
    _visit(payload)
    return pairs


def _query_match_list(payload: dict[str, Any], reducer_id: str) -> list[Any] | None:
    if reducer_id == "symbol_lookup":
        matches = payload.get("matches")
        return matches if isinstance(matches, list) else None
    if reducer_id == "symbol_references":
        references = payload.get("references")
        if isinstance(references, list):
            return references
        matches = payload.get("matches")
        return matches if isinstance(matches, list) else None
    return None


def _walk_payload(payload: dict[str, Any]) -> Iterable[tuple[str, Any]]:
    stack: list[tuple[str, Any]] = list(payload.items())
    while stack:
        key, value = stack.pop()
        yield key, value
        if isinstance(value, dict):
            stack.extend(value.items())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    stack.extend(item.items())


def _extract_span_text(repo_root: Path, file_path: str, span: list[int] | tuple[int, int]) -> str | None:
    if not span or len(span) != 2:
        return None
    try:
        start, end = int(span[0]), int(span[1])
    except Exception:
        return None
    if start <= 0 or end < start:
        return None
    full_path = repo_root / file_path
    try:
        text = full_path.read_text(encoding="utf-8")
    except Exception:
        return None
    lines = text.splitlines(keepends=True)
    if not lines:
        return None
    end = min(end, len(lines))
    start = min(start, end)
    return "".join(lines[start - 1 : end])


def _extract_span_bytes(
    repo_root: Path, file_path: str, start_byte: int, end_byte: int
) -> bytes | None:
    if start_byte < 0 or end_byte < start_byte:
        return None
    full_path = repo_root / file_path
    try:
        data = full_path.read_bytes()
    except Exception:
        return None
    if end_byte > len(data):
        return None
    return data[start_byte:end_byte]


def _extract_line_span_bytes(
    repo_root: Path, file_path: str, span: list[int] | tuple[int, int]
) -> bytes | None:
    if not span or len(span) != 2:
        return None
    try:
        start, end = int(span[0]), int(span[1])
    except Exception:
        return None
    if start <= 0 or end < start:
        return None
    full_path = repo_root / file_path
    try:
        data = full_path.read_bytes()
    except Exception:
        return None
    lines = data.splitlines(keepends=True)
    if not lines:
        return None
    end = min(end, len(lines))
    start = min(start, end)
    return b"".join(lines[start - 1 : end])


def _content_hash_matches_bytes(snippet: bytes, content_hash: str) -> bool:
    if not snippet:
        return False
    canonical = canonical_span_bytes(snippet)
    if not canonical:
        return False
    return hashlib.sha1(canonical).hexdigest() == content_hash


def _content_hash_candidates_bytes(snippet: bytes) -> list[bytes]:
    if not snippet:
        return []
    canonical = canonical_span_bytes(snippet)
    return [canonical] if canonical else []


def _line_span_hash_matches(snippet: str, line_span_hash: str) -> bool:
    if not snippet:
        return False
    canonical = canonical_span_text(snippet)
    if not canonical:
        return False
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest() == line_span_hash


def _snippet_preview(text: str) -> str:
    if len(text) <= HASH_SNIPPET_LIMIT:
        return text
    return text[:HASH_SNIPPET_LIMIT] + "..."


def _snippet_preview_bytes(data: bytes) -> str:
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    return _snippet_preview(text)


def _validate_paths(payload: dict[str, Any], paths: list[str]) -> tuple[int, list[str]]:
    present = 0
    missing: list[str] = []
    for path in paths:
        if _path_exists(payload, path):
            present += 1
        else:
            missing.append(path)
    return present, missing


def _path_exists(root: dict[str, Any], path: str) -> bool:
    parts = path.split(".")
    nodes: list[Any] = [root]
    for part in parts:
        next_nodes: list[Any] = []
        list_mode = part.endswith("[]")
        key = part[:-2] if list_mode else part
        for node in nodes:
            if not isinstance(node, dict) or key not in node:
                continue
            value = node[key]
            if list_mode:
                if isinstance(value, list):
                    if not value:
                        # Empty list satisfies nested-path requirement.
                        return True
                    next_nodes.extend(value)
            else:
                next_nodes.append(value)
        nodes = next_nodes
        if not nodes:
            return False
    return True


def _extract_path_values(root: dict[str, Any], path: str) -> list[Any] | None:
    parts = path.split(".")
    nodes: list[Any] = [root]
    for part in parts:
        next_nodes: list[Any] = []
        list_mode = part.endswith("[]")
        key = part[:-2] if list_mode else part
        for node in nodes:
            if not isinstance(node, dict) or key not in node:
                continue
            value = node[key]
            if list_mode:
                if isinstance(value, list):
                    next_nodes.extend(value)
            else:
                next_nodes.append(value)
        nodes = next_nodes
        if not nodes:
            return None
    return nodes


def _db_consistency(core_ids: set[str], artifact_ids: set[str]) -> float:
    if not core_ids and not artifact_ids:
        return 1.0
    union = core_ids | artifact_ids
    inter = core_ids & artifact_ids
    return len(inter) / len(union)


def _entity_query_term(entity: Entity) -> str:
    return entity.qualified_name.split(".")[-1]


def _select_query_term(entity: Entity, terms: set[str]) -> str:
    preferred = _entity_query_term(entity)
    if preferred and preferred in terms:
        return preferred
    stoplist = {"self", "cls", "args", "kwargs", "true", "false", "none"}
    candidates = [
        t for t in terms
        if len(t) >= 3 and t.lower() not in stoplist
    ]
    if candidates:
        return sorted(candidates)[0]
    return preferred


def _invocations_for_reducer(
    reducer_id: str,
    contract: dict[str, Any],
    sampled: list[Entity],
    *,
    request_key_map: dict[str, str] | None = None,
    query_terms: dict[str, str] | None = None,
) -> list[InvocationSpec]:
    modules = [e for e in sampled if e.kind == "module"]
    classes = [e for e in sampled if e.kind == "class"]
    callables = [e for e in sampled if e.kind in {"function", "method"}]
    invoke = contract.get("invoke") or {}
    entity_kind = invoke.get("entity")
    args = invoke.get("args") or {}
    defaults = invoke.get("defaults") or {}

    if entity_kind == "codebase":
        base_entities = [None]
    elif entity_kind == "module":
        base_entities = modules
    elif entity_kind == "class":
        base_entities = classes
    elif entity_kind == "callable":
        base_entities = callables
    elif entity_kind == "mixed":
        base_entities = modules + classes + callables
    else:
        if contract.get("scope") == "codebase":
            base_entities = [None]
        else:
            base_entities = modules + classes + callables

    invocations: list[InvocationSpec] = []
    for entity in base_entities:
        kwargs: dict[str, Any] = {}
        for key, source in args.items():
            if source == "module_id" and entity is not None:
                kwargs[key] = entity.structural_id
            elif source == "class_id" and entity is not None:
                kwargs[key] = entity.structural_id
            elif source == "callable_id" and entity is not None:
                kwargs[key] = entity.structural_id
            elif source == "query_term" and entity is not None:
                if query_terms and entity.structural_id in query_terms:
                    kwargs[key] = query_terms[entity.structural_id]
                else:
                    kwargs[key] = _entity_query_term(entity)
            elif source == "kind" and entity is not None:
                kwargs[key] = entity.kind
        kwargs.update(defaults)
        label = "primary"
        if request_key_map is not None and entity is not None:
            request_key_map[entity.structural_id] = inv_key_key(kwargs)
        invocations.append(InvocationSpec(entity=entity, kwargs=kwargs, label=label))

    if reducer_id == "concatenated_source":
        invocations = [
            InvocationSpec(
                entity=e, kwargs={"scope": "module", "module_id": e.structural_id}, label="primary"
            )
            for e in modules
        ] + [
            InvocationSpec(
                entity=e, kwargs={"scope": "class", "class_id": e.structural_id}, label="primary"
            )
            for e in classes
        ]
    if reducer_id == "fan_summary":
        invocations = []
        for entity in modules:
            invocations.append(
                InvocationSpec(entity=entity, kwargs={"module_id": entity.structural_id}, label="primary")
            )
        for entity in classes:
            invocations.append(
                InvocationSpec(entity=entity, kwargs={"class_id": entity.structural_id}, label="primary")
            )
        for entity in callables:
            invocations.append(
                InvocationSpec(entity=entity, kwargs={"callable_id": entity.structural_id}, label="primary")
            )

    if reducer_id in {"symbol_lookup", "symbol_references"}:
        invocations.append(
            InvocationSpec(
                entity=None,
                kwargs={"query": "__sciona_no_such_symbol__", "kind": "function", "limit": 5},
                label="negative_probe",
                is_negative=True,
            )
        )

    return invocations


def inv_key_key(kwargs: dict[str, Any]) -> str:
    return json.dumps(kwargs, sort_keys=True)


def _type_check(payload: dict[str, Any], type_rules: dict[str, str]) -> tuple[int, int, list[str]]:
    ok = 0
    missing: list[str] = []
    for key, type_name in type_rules.items():
        if key not in payload:
            missing.append(key)
            continue
        if _type_matches(payload[key], type_name):
            ok += 1
        else:
            missing.append(key)
    return ok, len(type_rules), missing


def _type_matches(value: Any, type_name: str) -> bool:
    if type_name == "str":
        return isinstance(value, str)
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "bool":
        return isinstance(value, bool)
    if type_name == "float":
        return isinstance(value, float)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "list":
        return isinstance(value, list)
    if type_name == "dict":
        return isinstance(value, dict)
    return False


def _list_policy_check(
    payload: dict[str, Any], allow_empty: Iterable[str], min_items: dict[str, int]
) -> tuple[int, int, list[str]]:
    ok = 0
    failures: list[str] = []
    allow_empty_set = set(allow_empty or [])
    for field, minimum in (min_items or {}).items():
        value = payload.get(field)
        if not isinstance(value, list):
            failures.append(f"min_items:{field}:{minimum}")
            continue
        if len(value) >= minimum:
            ok += 1
        else:
            failures.append(f"min_items:{field}:{minimum}")
    for field in allow_empty_set:
        value = payload.get(field)
        if isinstance(value, list):
            ok += 1
        else:
            failures.append(f"allow_empty:{field}")
    total = len(min_items or {}) + len(allow_empty_set)
    return ok, total, failures


def _invariant_check(payload: dict[str, Any], invariants: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    ok = 0
    failures: list[str] = []
    for rule in invariants:
        if "equals_len" in rule:
            count_field, list_field = rule["equals_len"]
            count_value = payload.get(count_field)
            list_value = payload.get(list_field)
            if isinstance(count_value, int) and isinstance(list_value, list):
                if count_value == len(list_value):
                    ok += 1
                else:
                    failures.append(f"equals_len:{count_field}:{list_field}")
            else:
                failures.append(f"equals_len:{count_field}:{list_field}")
        elif "min_items" in rule:
            field, minimum = rule["min_items"]
            value = payload.get(field)
            if isinstance(value, list) and isinstance(minimum, int) and len(value) >= minimum:
                ok += 1
            else:
                failures.append(f"min_items:{field}:{minimum}")
        elif "unique" in rule:
            field = rule["unique"]
            values = _extract_path_values(payload, field)
            if values is None:
                failures.append(f"unique:{field}")
            else:
                filtered = [v for v in values if v is not None]
                if len(set(filtered)) == len(filtered):
                    ok += 1
                else:
                    failures.append(f"unique:{field}")
        elif "non_negative" in rule:
            field = rule["non_negative"]
            value = payload.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                ok += 1
            else:
                failures.append(f"non_negative:{field}")
        elif "subset_of" in rule:
            left, right = rule["subset_of"]
            left_values = _extract_path_values(payload, left)
            right_values = _extract_path_values(payload, right)
            if left_values is None or right_values is None:
                failures.append(f"subset_of:{left}:{right}")
            else:
                if set(left_values) <= set(right_values):
                    ok += 1
                else:
                    failures.append(f"subset_of:{left}:{right}")
        else:
            failures.append(str(rule))
    return ok, len(invariants), failures


def _source_reducer_omission(
    reducer_id: str, payload_text: str, entity: Entity | None
) -> bool:
    if entity is None:
        return False
    payload = _maybe_json(payload_text)
    if not payload:
        return True

    if reducer_id == "concatenated_source":
        files = payload.get("files")
        if not isinstance(files, list):
            return True
        return entity.file_path not in {
            f.get("path") for f in files if isinstance(f, dict) and isinstance(f.get("path"), str)
        }
    if reducer_id == "callable_source":
        file_path = payload.get("file_path")
        source = payload.get("source")
        if not isinstance(file_path, str):
            return True
        if file_path != entity.file_path:
            return True
        return not isinstance(source, str) or not source.strip()
    return False


def _summarize_strengths(
    metrics: dict[str, Any],
    reducer_id: str,
    *,
    overlap_enabled: bool,
    structural_accuracy_enabled: bool,
) -> list[str]:
    strengths: list[str] = []
    if metrics["determinism_score"] >= 0.95:
        strengths.append("High determinism across repeated runs.")
    if structural_accuracy_enabled and metrics.get("structural_accuracy") is not None and metrics["structural_accuracy"] >= 0.95:
        strengths.append("Strong edge-level agreement with DB evidence.")
    if overlap_enabled and metrics.get("identifier_overlap") is not None and metrics["identifier_overlap"] >= 0.7:
        strengths.append("High evidence-term overlap with direct-code terms.")
    if metrics["length_stability"] >= 0.98:
        strengths.append("Stable payload length.")
    return strengths or ["No standout strengths observed."]


def _summarize_failures(
    metrics: dict[str, Any],
    reducer_id: str,
    *,
    overlap_enabled: bool,
    structural_accuracy_enabled: bool,
    unknown_enabled: bool,
) -> list[str]:
    failures: list[str] = []
    if unknown_enabled and metrics.get("unknown_id_qname_rate") not in (None, 0):
        failures.append("Unknown ids/qualified names present in evidence fields (may include out-of-scope symbols).")
    if metrics["omission_rate"] > 0:
        failures.append("Target entity omitted for some invocations.")
    if structural_accuracy_enabled and metrics.get("structural_accuracy") is not None and metrics["structural_accuracy"] < 0.9:
        failures.append("Dependency tuples include DB-unverified pairs.")
    if overlap_enabled and metrics.get("identifier_overlap") is not None and metrics["identifier_overlap"] < 0.5:
        failures.append("Low evidence-term overlap with direct-code terms.")
    return failures or ["No major failure mode observed."]


def _summarize_recommendations(
    metrics: dict[str, Any],
    reducer_id: str,
    *,
    overlap_enabled: bool,
    unknown_enabled: bool,
) -> list[str]:
    recs: list[str] = []
    if unknown_enabled and metrics.get("unknown_id_qname_rate") not in (None, 0):
        recs.append("Verify unknown ids/qnames; constrain to snapshot-resolved evidence if they are internal.")
    if metrics["determinism_score"] < 0.95:
        recs.append("Sort collections prior to serialization.")
    if overlap_enabled and metrics.get("identifier_overlap") is not None and metrics["identifier_overlap"] < 0.7:
        recs.append("Expose identifiers in evidence fields when available.")
    if metrics["token_length_variation_cv"] > 0.05:
        recs.append("Normalize optional sections and ordering.")
    if metrics.get("schema_compliance_score", 1.0) < 1.0:
        recs.append("Align payload fields to reducer contract (required/forbidden).")
    return recs or ["No adjustment needed under this protocol."]


def _build_executive_summary(
    reducer_results: dict[str, dict[str, Any]],
    sampled: list[Entity],
    calls_used: int,
) -> list[str]:
    valid_rows = [
        {"reducer_id": rid, **row}
        for rid, row in reducer_results.items()
        if "error" not in row
    ]
    if not valid_rows:
        return [
            "No reducers completed successfully.",
            "Review invocation errors in the per-reducer sections.",
        ]

    avg_determinism = _safe_mean([r["determinism_score"] for r in valid_rows], default=0.0) or 0.0
    structural_rows = [
        r for r in valid_rows if r.get("structural_accuracy") is not None
    ]
    avg_structural_accuracy = (
        _safe_mean([r["structural_accuracy"] for r in structural_rows], default=None)
        if structural_rows
        else None
    )
    overlap_rows = [
        r for r in valid_rows if r.get("identifier_overlap") is not None
    ]
    avg_identifier_overlap = (
        _safe_mean([r["identifier_overlap"] for r in overlap_rows], default=None)
        if overlap_rows
        else None
    )
    unknown_rows = [
        r for r in valid_rows if r.get("unknown_id_qname_rate") is not None
    ]
    avg_unknown_id_qname = (
        _safe_mean([r["unknown_id_qname_rate"] for r in unknown_rows], default=None)
        if unknown_rows
        else None
    )
    avg_error_rate = _safe_mean([r.get("error_rate", 0.0) for r in valid_rows], default=0.0) or 0.0

    empty_match_rows = [
        r for r in valid_rows if r.get("empty_match_rate") is not None
    ]
    avg_empty_match_rate = (
        (_safe_mean([r["empty_match_rate"] for r in empty_match_rows], default=None) or 0.0)
        if empty_match_rows
        else None
    )

    negative_probes = [
        (r.get("reducer_id"), r.get("negative_probes") or [])
        for r in valid_rows
        if r.get("negative_probes")
    ]
    neg_total = 0
    neg_ok = 0
    neg_fail_reducers: list[str] = []
    for reducer_id, probes in negative_probes:
        reducer_fail = False
        for probe in probes:
            neg_total += 1
            if probe.get("ok"):
                neg_ok += 1
            else:
                reducer_fail = True
        if reducer_fail and reducer_id is not None:
            neg_fail_reducers.append(reducer_id)

    lowest_semantic = (
        min(overlap_rows, key=lambda r: r["identifier_overlap"]) if overlap_rows else None
    )
    highest_hallucination = (
        max(unknown_rows, key=lambda r: r["unknown_id_qname_rate"])
        if unknown_rows
        else None
    )
    lowest_determinism = min(valid_rows, key=lambda r: r["determinism_score"])
    highest_determinism = max(valid_rows, key=lambda r: r["determinism_score"])

    summary: list[str] = []
    summary.append(
        f"Evaluated `{len(valid_rows)}` reducers on `{len(sampled)}` sampled entities "
        f"with `{calls_used}` reducer calls."
    )
    summary.append(
        "Overall quality snapshot: "
        f"avg_determinism=`{avg_determinism:.4f}`, "
        + (
            f"avg_structural_accuracy=`{avg_structural_accuracy:.4f}`, "
            if avg_structural_accuracy is not None
            else "avg_structural_accuracy=`n/a` (not applicable for some reducers), "
        )
        + (
            f"avg_identifier_overlap=`{avg_identifier_overlap:.4f}` (evidence-term overlap), "
            if avg_identifier_overlap is not None
            else "avg_identifier_overlap=`n/a` (not applicable for some reducers), "
        )
        + (
            f"avg_unknown_id_qname_rate=`{avg_unknown_id_qname:.4f}`, "
            if avg_unknown_id_qname is not None
            else "avg_unknown_id_qname_rate=`n/a` (not applicable for some reducers), "
        )
        + f"avg_error_rate=`{avg_error_rate:.4f}`."
    )
    if lowest_semantic is not None:
        summary.append(
            "Secondary signal outliers: "
            f"lowest evidence-term overlap=`{lowest_semantic['reducer_id']}` "
            f"({lowest_semantic['identifier_overlap']}); "
            + (
                f"highest unknown-id/qname rate=`{highest_hallucination['reducer_id']}` "
                f"({highest_hallucination['unknown_id_qname_rate']})."
                if highest_hallucination is not None
                else "highest unknown-id/qname rate=`n/a`."
            )
        )
    else:
        if highest_hallucination is not None:
            summary.append(
                "Secondary signal outliers: "
                f"highest unknown-id/qname rate=`{highest_hallucination['reducer_id']}` "
                f"({highest_hallucination['unknown_id_qname_rate']})."
            )
    if avg_empty_match_rate is not None:
        summary.append(
            "Query reducer signal: "
            f"avg_empty_match_rate=`{avg_empty_match_rate:.4f}` "
            f"across `{len(empty_match_rows)}` reducers."
        )
    if neg_total:
        ok_rate = _safe_ratio(neg_ok, neg_total, default=0.0)
        if neg_fail_reducers:
            failed = ", ".join(f"`{rid}`" for rid in sorted(set(neg_fail_reducers)))
            summary.append(
                "Negative probe outcomes: "
                f"pass_rate=`{ok_rate:.4f}`; failures in {failed}."
            )
        else:
            summary.append(
                "Negative probe outcomes: "
                f"pass_rate=`{ok_rate:.4f}` across `{neg_total}` probes."
            )
    if lowest_determinism["determinism_score"] == highest_determinism["determinism_score"]:
        summary.append(
            "Determinism uniform: "
            f"`{lowest_determinism['determinism_score']}` across reducers."
        )
    else:
        summary.append(
            "Stability highlight: "
            f"lowest determinism=`{lowest_determinism['reducer_id']}` "
            f"({lowest_determinism['determinism_score']})."
        )
    return summary


def _build_blind_summary(reducer_results: dict[str, dict[str, Any]]) -> list[str]:
    rows = [row for row in reducer_results.values() if "error" not in row and row.get("blind")]
    if not rows:
        return ["No blind validation results available."]
    avg_blind_error = _safe_mean([r["blind"]["blind_error_rate"] for r in rows], default=0.0) or 0.0
    avg_id = _safe_mean([r["blind"]["id_resolution_rate"] for r in rows], default=0.0) or 0.0
    avg_span = _safe_mean([r["blind"]["file_span_valid_rate"] for r in rows], default=0.0) or 0.0
    avg_count = _safe_mean([r["blind"]["count_consistency_rate"] for r in rows], default=0.0) or 0.0
    avg_span_hash = _safe_mean([r["blind"]["line_span_hash_match_rate"] for r in rows], default=0.0) or 0.0
    avg_hash = _safe_mean([r["blind"]["content_hash_match_rate"] for r in rows], default=0.0) or 0.0
    worst = max(rows, key=lambda r: r["blind"]["blind_error_rate"])
    diag_total = sum(int(r["blind"].get("hash_diagnostics_total", 0) or 0) for r in rows)
    return [
        f"avg_blind_error_rate=`{avg_blind_error:.4f}`; "
        f"avg_id_resolution=`{avg_id:.4f}`; "
        f"avg_file_span_valid=`{avg_span:.4f}`; "
        f"avg_count_consistency=`{avg_count:.4f}`; "
        f"avg_line_span_hash_match=`{avg_span_hash:.4f}`; "
        f"avg_content_hash_match=`{avg_hash:.4f}`.",
        f"worst_blind_error_rate=`{worst['blind']['blind_error_rate']}`.",
        f"hash_diagnostics_total=`{diag_total}` (per-reducer cap={MAX_HASH_DIAGNOSTICS}).",
    ]


def _load_thresholds(path: Path | None) -> dict[str, float]:
    if path is None:
        return dict(DEFAULT_THRESHOLDS)
    if not path.exists():
        return dict(DEFAULT_THRESHOLDS)
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        data = json.loads(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return dict(DEFAULT_THRESHOLDS)
    merged = dict(DEFAULT_THRESHOLDS)
    for key, value in data.items():
        if isinstance(value, (int, float)):
            merged[key] = float(value)
    return merged


def _get_sciona_version() -> str | None:
    try:
        return importlib.metadata.version("sciona")
    except Exception:
        return None


def _get_pkg_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None


def _file_sha1(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except Exception:
        return None
    return hashlib.sha1(data).hexdigest()


def _collect_overall_metrics(reducer_results: dict[str, dict[str, Any]]) -> dict[str, float]:
    rows = [row for row in reducer_results.values() if "error" not in row]
    if not rows:
        return {}
    avg_blind_error = sum(r["blind"]["blind_error_rate"] for r in rows) / len(rows)
    avg_content_hash = sum(r["blind"]["content_hash_match_rate"] for r in rows) / len(rows)
    empty_rows = [r for r in rows if r.get("empty_match_rate") is not None]
    avg_empty = (
        sum(r["empty_match_rate"] for r in empty_rows) / len(empty_rows)
        if empty_rows
        else None
    )
    hash_total = sum(len(r["blind"].get("hash_diagnostics", []) or []) for r in rows)
    return {
        "avg_blind_error_rate": round(avg_blind_error, 4),
        "avg_content_hash_match_rate": round(avg_content_hash, 4),
        "avg_empty_match_rate": round(avg_empty, 4) if avg_empty is not None else None,
        "hash_diagnostics_total": hash_total,
    }


def _baseline_diff(
    current: dict[str, Any],
    baseline: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    summary: list[str] = []
    regressions: list[str] = []

    cur_overall = _collect_overall_metrics(current["reducers"])
    base_overall = _collect_overall_metrics(baseline.get("reducers", {}))
    if cur_overall and base_overall:
        delta_blind = cur_overall["avg_blind_error_rate"] - base_overall.get("avg_blind_error_rate", 0.0)
        delta_hash = cur_overall["avg_content_hash_match_rate"] - base_overall.get(
            "avg_content_hash_match_rate", 0.0
        )
        delta_empty = None
        if cur_overall.get("avg_empty_match_rate") is not None and base_overall.get("avg_empty_match_rate") is not None:
            delta_empty = cur_overall["avg_empty_match_rate"] - base_overall["avg_empty_match_rate"]
        delta_diag = cur_overall["hash_diagnostics_total"] - base_overall.get("hash_diagnostics_total", 0)

        summary.append(
            "Overall deltas: "
            f"avg_blind_error_rate={delta_blind:+.4f}, "
            f"avg_content_hash_match_rate={delta_hash:+.4f}, "
            + (
                f"avg_empty_match_rate={delta_empty:+.4f}, " if delta_empty is not None else ""
            )
            + f"hash_diagnostics_total={delta_diag:+d}."
        )

        if delta_blind > thresholds["blind_error_rate_increase"]:
            regressions.append("avg_blind_error_rate increased beyond threshold.")
        if delta_hash < -thresholds["content_hash_match_drop"]:
            regressions.append("avg_content_hash_match_rate dropped beyond threshold.")
        if delta_empty is not None and delta_empty > thresholds["empty_match_rate_increase"]:
            regressions.append("avg_empty_match_rate increased beyond threshold.")
        if delta_diag > thresholds["hash_diagnostics_increase"]:
            regressions.append("hash_diagnostics_total increased beyond threshold.")

        if cur_overall["avg_blind_error_rate"] > thresholds["blind_error_rate_max"]:
            regressions.append("avg_blind_error_rate exceeds absolute maximum.")
        if cur_overall["avg_content_hash_match_rate"] < thresholds["content_hash_match_min"]:
            regressions.append("avg_content_hash_match_rate below absolute minimum.")
        if cur_overall["hash_diagnostics_total"] > thresholds["hash_diagnostics_max"]:
            regressions.append("hash_diagnostics_total exceeds absolute maximum.")
        if (
            cur_overall.get("avg_empty_match_rate") is not None
            and cur_overall["avg_empty_match_rate"] > thresholds["empty_match_rate_max"]
        ):
            regressions.append("avg_empty_match_rate exceeds absolute maximum.")

    # Per-reducer identifier overlap regression check.
    cur_rows = current["reducers"]
    base_rows = baseline.get("reducers", {})
    overlap_regressions: list[str] = []
    for reducer_id, row in cur_rows.items():
        if "error" in row:
            continue
        base_row = base_rows.get(reducer_id)
        if not base_row or "error" in base_row:
            continue
        if row.get("identifier_overlap") is None:
            continue
        if base_row.get("identifier_overlap") is None:
            continue
        delta = row.get("identifier_overlap", 1.0) - base_row.get("identifier_overlap", 1.0)
        if delta < -thresholds["identifier_overlap_drop"]:
            overlap_regressions.append(reducer_id)
    if overlap_regressions:
        regressions.append(
            "identifier_overlap (evidence-term overlap) dropped beyond threshold for: "
            + ", ".join(f"`{rid}`" for rid in sorted(overlap_regressions))
        )

    return {
        "summary": summary,
        "regressions": regressions,
        "thresholds": thresholds,
        "current_overall": cur_overall,
        "baseline_overall": base_overall,
    }


def _build_consolidated_summary(reducer_results: dict[str, dict[str, Any]]) -> list[str]:
    rows = [row for row in reducer_results.values() if "error" not in row]
    if not rows:
        return ["No reducers completed successfully."]
    avg_schema = _safe_mean([r.get("schema_compliance_score", 1.0) for r in rows], default=0.0) or 0.0
    avg_cov = _safe_mean([r.get("coverage_score", 0.0) for r in rows], default=0.0) or 0.0
    avg_err = _safe_mean([r.get("error_rate", 0.0) for r in rows], default=0.0) or 0.0
    return [
        f"avg_schema_compliance=`{avg_schema:.4f}`, avg_coverage=`{avg_cov:.4f}`, avg_error_rate=`{avg_err:.4f}`.",
    ]


def _coherence_checks(
    payloads: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    call_graphs = payloads.get("call_neighbors", {})
    callsites = payloads.get("callsite_index", {})
    overlaps: list[float] = []
    raw_overlaps: list[float] = []
    for key, cg in call_graphs.items():
        cs = callsites.get(key)
        if not cs:
            continue
        cg_ids = {
            item.get("structural_id")
            for item in (cg.get("callers") or []) + (cg.get("callees") or [])
            if isinstance(item, dict)
        }
        cs_ids = set()
        for edge in cs.get("edges") or []:
            if isinstance(edge, dict):
                cs_ids.add(edge.get("caller_id"))
                cs_ids.add(edge.get("callee_id"))
        cg_ids.discard(None)
        cs_ids.discard(None)
        if cg_ids or cs_ids:
            raw_overlaps.append(_jaccard(cg_ids, cs_ids))
        if key:
            cg_ids.discard(key)
            cs_ids.discard(key)
        if cg_ids or cs_ids:
            overlaps.append(_jaccard(cg_ids, cs_ids))
    if overlaps:
        results["call_neighbors_vs_callsite_index"] = {
            "expectation": "overlap",
            "normalization": "caller/callee ids excluding self id",
            "mean_jaccard_raw": round(_safe_mean(raw_overlaps, default=None), 4) if raw_overlaps else None,
            "mean_jaccard": round(_safe_mean(overlaps, default=0.0) or 0.0, 4),
            "pairs": len(overlaps),
        }

    import_refs = payloads.get("import_targets", {})
    importers = payloads.get("importers_index", {})
    target_overlaps: list[float] = []
    for key, ir in import_refs.items():
        ii = importers.get(key)
        if not ii:
            continue
        ir_targets = {
            item.get("module_structural_id")
            for item in ir.get("targets") or []
            if isinstance(item, dict)
        }
        ii_targets = {
            item.get("module_structural_id")
            for item in ii.get("targets") or []
            if isinstance(item, dict)
        }
        ir_targets.discard(None)
        ii_targets.discard(None)
        if ir_targets or ii_targets:
            target_overlaps.append(_jaccard(ir_targets, ii_targets))
    if target_overlaps:
        results["import_targets_vs_importers_index"] = {
            "expectation": "equivalent_targets",
            "mean_jaccard": round(_safe_mean(target_overlaps, default=0.0) or 0.0, 4),
            "pairs": len(target_overlaps),
        }

    module_map = payloads.get("module_file_map", {})
    outlines = payloads.get("file_outline", {})
    file_hits = 0
    file_total = 0
    for key, fo in outlines.items():
        if not isinstance(fo, dict):
            continue
        file_paths = {
            item.get("file_path")
            for item in fo.get("files") or []
            if isinstance(item, dict)
        }
        file_paths.discard(None)
        if not file_paths:
            continue
        map_entries = module_map.get(key)
        if not map_entries or not isinstance(map_entries, dict):
            continue
        map_paths = {
            item.get("file_path")
            for item in map_entries.get("modules") or []
            if isinstance(item, dict)
        }
        map_paths.discard(None)
        if not map_paths:
            continue
        file_total += 1
        if file_paths.issubset(map_paths):
            file_hits += 1
    if file_total:
        results["module_file_map_vs_file_outline"] = {
            "expectation": "subset",
            "subset_rate": round(file_hits / file_total, 4),
            "pairs": file_total,
        }

    return results


# ---- Evaluation Phases ----


def _resolve_output_paths(args: argparse.Namespace, repo_root: Path) -> tuple[Path, Path, str]:
    repo_prefix = f"{repo_root.name}_"
    report_prefix = f"[{repo_root.name}] "
    out_json = args.out_json
    if not out_json.is_absolute():
        out_json = (REPORTS_DIR / out_json).resolve()
    out_md = args.out_md
    if not out_md.is_absolute():
        out_md = (REPORTS_DIR / out_md).resolve()
    if not out_json.name.startswith(repo_prefix):
        out_json = out_json.with_name(f"{repo_prefix}{out_json.name}")
    if not out_md.name.startswith(repo_prefix):
        out_md = out_md.with_name(f"{repo_prefix}{out_md.name}")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    return out_json, out_md, report_prefix


def _prepare_db_paths(
    args: argparse.Namespace, repo_root: Path
) -> tuple[Path, Path, bool, bool]:
    db_path = get_db_path(repo_root)
    artifact_path = get_artifact_db_path(repo_root)
    effective_db_path = db_path
    effective_artifact_path = artifact_path
    readonly_core = _use_readonly_db(db_path, args.db_readonly)
    readonly_artifact = _use_readonly_db(artifact_path, args.db_readonly)
    if readonly_core:
        effective_db_path = _copy_db_to_tmp(db_path, label="coredb")
    if readonly_artifact and artifact_path.exists():
        effective_artifact_path = _copy_db_to_tmp(artifact_path, label="artifactdb")
    return effective_db_path, effective_artifact_path, readonly_core, readonly_artifact


def _resolve_snapshot_id(
    effective_db_path: Path, repo_root: Path, readonly_core: bool
) -> tuple[str, Path, bool]:
    try:
        with _open_core_db(effective_db_path, repo_root=repo_root, read_only=readonly_core) as conn:
            snapshot_id = snapshot_policy.resolve_latest_snapshot(conn)
            return snapshot_id, effective_db_path, readonly_core
    except sqlite3.OperationalError:
        effective_db_path = _copy_db_to_tmp(effective_db_path, label="coredb")
        with _open_core_db(effective_db_path, repo_root=repo_root, read_only=True) as conn:
            snapshot_id = snapshot_policy.resolve_latest_snapshot(conn)
            return snapshot_id, effective_db_path, True


def _prepare_sampling(
    repo_root: Path,
    effective_db_path: Path,
    snapshot_id: str,
    args: argparse.Namespace,
    ctx: EvalContext,
) -> SamplingData:
    all_entities = _load_entities(repo_root, effective_db_path, snapshot_id)
    population_by_language: dict[str, int] = defaultdict(int)
    population_by_kind: dict[str, int] = defaultdict(int)
    for e in all_entities:
        population_by_language[e.language] += 1
        population_by_kind[e.kind] += 1
    sampled = _sample_balanced(all_entities, args.nodes, args.seed)
    sampled_ids = {e.structural_id for e in sampled}
    sampled_qnames = {e.qualified_name for e in sampled}
    direct_terms: dict[str, set[str]] = {}
    direct_method_by_entity: dict[str, str] = {}
    query_terms: dict[str, str] = {}
    for entity in sampled:
        terms, method = _code_terms(repo_root, entity, ctx)
        direct_terms[entity.structural_id] = terms
        direct_method_by_entity[entity.structural_id] = method
        query_terms[entity.structural_id] = _select_query_term(entity, terms)
    return SamplingData(
        sampled=sampled,
        sampled_ids=sampled_ids,
        sampled_qnames=sampled_qnames,
        direct_terms=direct_terms,
        direct_method_by_entity=direct_method_by_entity,
        query_terms=query_terms,
        population_by_language=dict(population_by_language),
        population_by_kind=dict(population_by_kind),
    )


def _collect_ground_truth(
    effective_db_path: Path,
    effective_artifact_path: Path,
    artifact_path: Path,
) -> GroundTruth:
    core_sql = sqlite3.connect(effective_db_path)
    gt_qnames = {r[0] for r in core_sql.execute("SELECT DISTINCT qualified_name FROM node_instances")}
    gt_module_qnames = {
        r[0]
        for r in core_sql.execute(
            """
            SELECT DISTINCT ni.qualified_name
            FROM node_instances AS ni
            JOIN structural_nodes AS sn
              ON sn.structural_id = ni.structural_id
            WHERE sn.node_type = 'module'
            """
        )
    }
    gt_ids = {r[0] for r in core_sql.execute("SELECT structural_id FROM structural_nodes")}
    gt_edges = {(r[0], r[1]) for r in core_sql.execute("SELECT src_structural_id, dst_structural_id FROM edges")}
    core_sql.close()

    art_nodes: set[str] = set()
    art_edges: set[tuple[str, str]] = set()
    if artifact_path.exists():
        try:
            art_sql = sqlite3.connect(effective_artifact_path)
        except sqlite3.OperationalError:
            effective_artifact_path = _copy_db_to_tmp(artifact_path, label="artifactdb")
            art_sql = sqlite3.connect(effective_artifact_path)
        art_nodes = {r[0] for r in art_sql.execute("SELECT node_id FROM graph_nodes")}
        art_edges = {(r[0], r[1]) for r in art_sql.execute("SELECT src_node_id, dst_node_id FROM graph_edges")}
        art_sql.close()

    return GroundTruth(
        gt_qnames=gt_qnames,
        gt_module_qnames=gt_module_qnames,
        gt_ids=gt_ids,
        gt_edges=gt_edges,
        art_nodes=art_nodes,
        art_edges=art_edges,
    )


def _evaluate_reducers(
    *,
    repo_root: Path,
    effective_db_path: Path,
    effective_artifact_path: Path,
    artifact_path: Path,
    readonly_core: bool,
    readonly_artifact: bool,
    snapshot_id: str,
    reducer_ids: list[str],
    sampled: list[Entity],
    query_terms: dict[str, str],
    contracts: dict[str, dict[str, Any]],
    ctx: EvalContext,
    args: argparse.Namespace,
    gt: GroundTruth,
    sampled_ids: set[str],
    sampled_qnames: set[str],
    direct_terms: dict[str, set[str]],
    direct_method_by_entity: dict[str, str],
) -> EvalOutput:
    calls_used = 0
    invocations_total = 0
    invocation_errors = 0
    reducer_results: dict[str, ReducerMetrics] = {}
    coherence_store: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    blind_rates_by_language: dict[str, list[BlindSummary]] = defaultdict(list)
    blind_rates_by_kind: dict[str, list[BlindSummary]] = defaultdict(list)
    hash_appendix: list[dict[str, Any]] = []

    artifact_scope = (
        _open_artifact_db(
            effective_artifact_path, repo_root=repo_root, read_only=readonly_artifact
        )
        if effective_artifact_path.exists()
        else nullcontext(None)
    )
    with _open_core_db(effective_db_path, repo_root=repo_root, read_only=readonly_core) as conn:
        with artifact_scope as aconn:
            with use_artifact_connection(aconn):
                for reducer_id in reducer_ids:
                    reducer = load_reducer(reducer_id)
                    contract = _contract_requirements(contracts, reducer_id)
                    reducer_type = _reducer_type(contract)
                    overlap_enabled = _overlap_enabled(contract, reducer_id)
                    structural_accuracy_enabled = _structural_accuracy_enabled(contract)
                    unknown_enabled = _unknown_checks_enabled(contract, reducer_id)
                    unknown_policy = contract.get("unknown_policy", {})
                    invocations = _invocations_for_reducer(
                        reducer_id,
                        contract,
                        sampled,
                        query_terms=query_terms,
                    )
                    if not invocations:
                        reducer_results[reducer_id] = {
                            "error": "no compatible sampled entities for this reducer",
                        }
                        continue

                    by_invocation: dict[str, list[tuple[str, str, Entity | None]]] = defaultdict(list)
                    errors: list[str] = []
                    echo_fields = contract.get("echo_fields", [])
                    negative_probe_results: list[dict[str, Any]] = []
                    negative_inv_keys: set[str] = set()
                    durations_ms: list[float] = []
                    for inv in invocations:
                        entity = inv.entity
                        kwargs = inv.kwargs
                        inv_key = json.dumps(kwargs, sort_keys=True)
                        run_count = 1 if inv.is_negative else args.runs
                        if inv.is_negative:
                            negative_inv_keys.add(inv_key)
                        for _ in range(run_count):
                            invocations_total += 1
                            try:
                                start = time.perf_counter()
                                rendered = reducer.render(snapshot_id, conn, repo_root, **kwargs)
                                durations_ms.append((time.perf_counter() - start) * 1000)
                            except Exception as exc:  # noqa: BLE001
                                errors.append(f"{inv_key}: {type(exc).__name__}: {exc}")
                                invocation_errors += 1
                                break
                            calls_used += 1
                            normalized = _normalize_payload_text(rendered, echo_fields)
                            by_invocation[inv_key].append((normalized, rendered, entity))
                            if inv.is_negative:
                                payload = _maybe_json(rendered)
                                matches = payload.get("matches") if isinstance(payload, dict) else None
                                references = payload.get("references") if isinstance(payload, dict) else None
                                ok = False
                                if isinstance(matches, list) and not matches:
                                    if reducer_id == "symbol_references":
                                        ok = isinstance(references, list) and not references
                                    else:
                                        ok = True
                                negative_probe_results.append(
                                    {
                                        "args": kwargs,
                                        "ok": ok,
                                        "matches": len(matches) if isinstance(matches, list) else None,
                                        "references": len(references) if isinstance(references, list) else None,
                                    }
                                )
                            else:
                                payload = _maybe_json(rendered)
                                if payload:
                                    key = entity.structural_id if entity is not None else inv_key
                                    coherence_store[reducer_id][key] = payload

                    if not by_invocation:
                        reducer_results[reducer_id] = {
                            "error": "all invocations failed",
                            "errors_total": len(errors),
                            "errors_sample": errors[:20],
                        }
                        continue

                    structural_variance: list[float] = []
                    semantic_variance: list[float] = []
                    length_cv: list[float] = []
                    determinism: list[float] = []
                    ordering_only = 0
                    omissions = 0
                    hallucinated = 0
                    dep_total = 0
                    dep_bad = 0
                    sem_hits = 0
                    sem_total = 0
                    symbol_checks = 0
                    dependency_checks = 0
                    schema_present = 0
                    unknown_out_of_scope = 0.0
                    unknown_out_of_sample = 0.0
                    unknown_unresolved_in_scope = 0.0
                    unknown_resolution_failure = 0.0
                    query_match_checks = 0
                    query_empty_matches = 0
                    schema_required = 0
                    paths_present = 0
                    paths_required = 0
                    missing_paths: set[str] = set()
                    forbidden_hits = 0
                    coverage_hits = 0
                    payload_key_union: set[str] = set()
                    blind_rates: list[BlindSummary] = []
                    type_mismatches: set[str] = set()
                    invariant_failures: set[str] = set()
                    direct_span_checks = 0
                    direct_span_hits = 0

                    required_fields = set(contract.get("required_fields", []))
                    optional_fields = set(contract.get("optional_fields", []))
                    forbidden_fields = set(contract.get("forbidden_fields", []))
                    echo_fields_set = set(contract.get("echo_fields", []))
                    evidence_fields = set(contract.get("evidence_fields", []))
                    allowed_fields = required_fields | optional_fields | echo_fields_set | evidence_fields

                    for inv_key, runs in by_invocation.items():
                        if inv_key in negative_inv_keys:
                            continue
                        texts = [t for t, _, _ in runs]
                        hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]
                        uniq = len(set(hashes))
                        structural_variance.append((uniq - 1) / max(1, len(hashes) - 1))
                        determinism.append(max(hashes.count(h) for h in set(hashes)) / len(hashes))

                        order_hashes: list[str] = []
                        order_invariant_hashes: list[str] = []
                        for _, raw_text, _ in runs:
                            payload = _maybe_json(raw_text)
                            if payload is None:
                                continue
                            order_hashes.append(
                                hashlib.sha256(
                                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                                ).hexdigest()
                            )
                            order_invariant_hashes.append(
                                hashlib.sha256(
                                    _order_invariant_dump(payload).encode("utf-8")
                                ).hexdigest()
                            )
                        if order_hashes and order_invariant_hashes:
                            if len(set(order_hashes)) > 1 and len(set(order_invariant_hashes)) == 1:
                                ordering_only += 1

                        sets = [_token_set(t) for t in texts]
                        sims: list[float] = []
                        for i in range(len(sets)):
                            for j in range(i + 1, len(sets)):
                                sims.append(_jaccard(sets[i], sets[j]))
                        semantic_variance.append(1 - (_safe_mean(sims, default=1.0) or 1.0))

                        lens = [len(re.findall(r"\S+", t)) for t in texts]
                        mean = _safe_mean(lens, default=0.0) or 0.0
                        length_cv.append((statistics.pstdev(lens) / mean) if mean else 0.0)

                        first_text, raw_text, entity = runs[0]
                        first_payload = _maybe_json(raw_text)
                        (
                            present,
                            required,
                            forbidden,
                            required_paths,
                            missing,
                            type_ok,
                            type_total,
                            type_missing,
                            invariant_ok,
                            invariant_total,
                            invariant_missing,
                        ) = _schema_compliance(
                            first_payload, contract
                        )
                        schema_present += present
                        schema_required += required
                        forbidden_hits += forbidden
                        paths_required += required_paths
                        present_paths = required_paths - len(missing)
                        paths_present += present_paths
                        schema_present += present_paths
                        schema_required += required_paths
                        missing_paths.update(missing)
                        type_mismatches.update(type_missing)
                        invariant_failures.update(invariant_missing)
                        type_present = type_ok
                        type_required = type_total
                        invariant_present = invariant_ok
                        invariant_required = invariant_total
                        if type_total:
                            schema_present += type_present
                            schema_required += type_required
                        if invariant_total:
                            schema_present += invariant_present
                            schema_required += invariant_required
                        if first_payload:
                            payload_key_union.update(first_payload.keys())
                        blind_result = _blind_checks(
                            first_payload,
                            gt.gt_ids,
                            repo_root,
                            reducer_id=reducer_id,
                            entity=entity,
                        )
                        blind_rates.append(blind_result)
                        if entity is not None:
                            blind_rates_by_language[entity.language].append(blind_result)
                            blind_rates_by_kind[entity.kind].append(blind_result)
                        if blind_result.get("hash_diagnostics") and len(hash_appendix) < MAX_APPENDIX_DIAGNOSTICS:
                            for diag in blind_result.get("hash_diagnostics", []):
                                if len(hash_appendix) >= MAX_APPENDIX_DIAGNOSTICS:
                                    break
                                hash_appendix.append(diag)
                        if first_payload:
                            match_list = _query_match_list(first_payload, reducer_id)
                        else:
                            match_list = None
                        if match_list is not None:
                            query_match_checks += 1
                            if not match_list:
                                query_empty_matches += 1
                            coverage_hits += 1
                        elif required and present == required:
                            coverage_hits += 1
                        elif not required and first_payload:
                            coverage_hits += 1
                        if entity is None:
                            continue

                        if contract.get("required_fields"):
                            missing = contract.get("required_fields", [])
                            if first_payload:
                                missing = [k for k in missing if k not in first_payload]
                            omissions += len(missing)
                        elif reducer_id in SOURCE_REDUCERS:
                            omissions += int(_source_reducer_omission(reducer_id, first_text, entity))
                        else:
                            omissions += int(
                                entity.qualified_name not in first_text and entity.structural_id not in first_text
                            )

                        # Symbol checks are reducer-specific: skip free-form source reducers.
                        if unknown_enabled and first_payload:
                            evidence_payload = first_payload
                            if echo_fields:
                                evidence_payload = _prune_echo_fields(
                                    evidence_payload, set(echo_fields)
                                )
                            if evidence_fields:
                                evidence_payload = {
                                    key: value
                                    for key, value in evidence_payload.items()
                                    if key in evidence_fields
                                }
                            elif required_fields:
                                evidence_payload = {
                                    key: value
                                    for key, value in evidence_payload.items()
                                    if key in required_fields
                                }
                            evidence_payload = _drop_content_hash_fields(evidence_payload)
                            idtokens, qtokens = _collect_evidence_identifiers(evidence_payload)
                            allow_suffix = bool(contract.get("qname_allow_suffix"))
                            out_of_scope = 0
                            out_of_sample = 0
                            unresolved_in_scope = 0
                            resolution_failure = 0
                            for value in qtokens:
                                if not value or value.strip() != value:
                                    resolution_failure += 1
                                    continue
                                if _qname_matches(value, gt.gt_qnames, allow_suffix=allow_suffix):
                                    if not _qname_in_sample(value, sampled_qnames, allow_suffix=allow_suffix):
                                        out_of_sample += 1
                                else:
                                    if _qname_in_scope(
                                        value, gt.gt_module_qnames, allow_suffix=allow_suffix
                                    ):
                                        unresolved_in_scope += 1
                                    else:
                                        out_of_scope += 1
                            for value in idtokens:
                                if value in gt.gt_ids or value in gt.art_nodes:
                                    if value not in sampled_ids:
                                        out_of_sample += 1
                                else:
                                    unresolved_in_scope += 1
                            if qtokens or idtokens:
                                total_tokens = max(1, len(qtokens) + len(idtokens))
                                unknown_total = _unknown_penalty(
                                    unknown_policy,
                                    out_of_scope=out_of_scope,
                                    out_of_sample=out_of_sample,
                                    unresolved_in_scope=unresolved_in_scope,
                                    resolution_failure=resolution_failure,
                                )
                                hallucinated += unknown_total / total_tokens
                                unknown_out_of_scope += out_of_scope / total_tokens
                                unknown_out_of_sample += out_of_sample / total_tokens
                                unknown_unresolved_in_scope += unresolved_in_scope / total_tokens
                                unknown_resolution_failure += resolution_failure / total_tokens
                            symbol_checks += len(qtokens) + len(idtokens)

                        for src, dst in re.findall(
                            r"([0-9a-f]{40})[^0-9a-f]{1,40}([0-9a-f]{40})", raw_text
                        ):
                            dep_total += 1
                            dependency_checks += 1
                            if (src, dst) not in gt.gt_edges and (src, dst) not in gt.art_edges:
                                dep_bad += 1

                        expected = direct_terms.get(entity.structural_id, set())
                        if expected and overlap_enabled:
                            if reducer_id in SOURCE_REDUCERS:
                                sem_hits += sum(1 for term in expected if term in raw_text)
                                sem_total += len(expected)
                            elif first_payload:
                                semantic_payload = first_payload
                                if echo_fields:
                                    semantic_payload = _prune_echo_fields(
                                        semantic_payload, set(echo_fields)
                                    )
                                if evidence_fields:
                                    semantic_payload = {
                                        key: value
                                        for key, value in semantic_payload.items()
                                        if key in evidence_fields
                                    }
                                elif required_fields:
                                    semantic_payload = {
                                        key: value
                                        for key, value in semantic_payload.items()
                                        if key in required_fields
                                    }
                                semantic_payload = _drop_content_hash_fields(semantic_payload)
                                semantic_tokens = _semantic_tokens_from_payload(
                                    semantic_payload
                                )
                                if semantic_tokens:
                                    sem_hits += sum(1 for term in expected if term in semantic_tokens)
                                    sem_total += len(expected)

                        if (
                            first_payload
                            and entity.kind in {"class", "function", "method"}
                            and isinstance(first_payload.get("file_path"), str)
                            and isinstance(first_payload.get("line_span"), list)
                        ):
                            snippet = _extract_span_text(
                                repo_root, first_payload["file_path"], first_payload["line_span"]
                            )
                            if snippet is not None:
                                direct_span_checks += 1
                                name = entity.qualified_name.split(".")[-1]
                                if name in snippet:
                                    direct_span_hits += 1

                    invocation_count = len(by_invocation)
                    avg_cv = _safe_mean(length_cv, default=0.0) or 0.0
                    ordering_instability = ordering_only / max(1, invocation_count)
                    schema_compliance = (
                        (schema_present / max(1, schema_required)) if schema_required else 1.0
                    )
                    error_rate = (len(errors) / max(1, invocation_count))
                    coverage_score = coverage_hits / max(1, invocation_count)
                    unknown_payload_keys = sorted(payload_key_union - allowed_fields - forbidden_fields)
                    blind_summary = _aggregate_blind(blind_rates)
                    empty_match_rate = None
                    if query_match_checks:
                        empty_match_rate = round(query_empty_matches / query_match_checks, 4)
                    structural_accuracy = (
                        round(1 - (dep_bad / dep_total), 4) if dep_total else 1.0
                    )
                    if not structural_accuracy_enabled:
                        structural_accuracy = None
                    identifier_overlap = round(sem_hits / sem_total, 4) if sem_total else 1.0
                    if not overlap_enabled:
                        identifier_overlap = None
                    unknown_rate = (
                        round(hallucinated / max(1, invocation_count), 4)
                        if unknown_enabled
                        else None
                    )
                    unknown_out_scope = (
                        round(unknown_out_of_scope / max(1, invocation_count), 4)
                        if unknown_enabled
                        else None
                    )
                    unknown_out_sample = (
                        round(unknown_out_of_sample / max(1, invocation_count), 4)
                        if unknown_enabled
                        else None
                    )
                    unknown_unresolved = (
                        round(unknown_unresolved_in_scope / max(1, invocation_count), 4)
                        if unknown_enabled
                        else None
                    )
                    unknown_resolution = (
                        round(unknown_resolution_failure / max(1, invocation_count), 4)
                        if unknown_enabled
                        else None
                    )
                    latency_avg = (
                        round(_safe_mean(durations_ms, default=None), 4)
                        if durations_ms
                        else None
                    )
                    latency_p95 = (
                        round(_percentile(durations_ms, 0.95), 4)
                        if durations_ms
                        else None
                    )
                    latency_max = (
                        round(max(durations_ms), 4) if durations_ms else None
                    )
                    metrics: ReducerMetrics = {
                        "samples": sum(len(v) for v in by_invocation.values()),
                        "invocations": invocation_count,
                        "inference": {"temperature": 0.0, "seed": args.seed},
                        "reducer_type": reducer_type,
                        "structural_variance": round(_safe_mean(structural_variance, default=0.0) or 0.0, 4),
                        "semantic_variance": round(_safe_mean(semantic_variance, default=0.0) or 0.0, 4),
                        "token_length_variation_cv": round(avg_cv, 4),
                        "unknown_id_qname_rate": unknown_rate,
                        "unknown_id_qname_out_of_scope_rate": unknown_out_scope,
                        "unknown_id_qname_out_of_sample_rate": unknown_out_sample,
                        "unknown_id_qname_unresolved_in_scope_rate": unknown_unresolved,
                        "unknown_id_qname_resolution_failure_rate": unknown_resolution,
                        "omission_rate": round(omissions / max(1, invocation_count), 4),
                        "structural_accuracy": structural_accuracy,
                        "identifier_overlap": identifier_overlap,
                        "length_stability": round(1 / (1 + avg_cv), 4),
                        "ordering_instability_rate": round(ordering_instability, 4),
                        "determinism_score": round(_safe_mean(determinism, default=1.0) or 1.0, 4),
                        "schema_compliance_score": round(schema_compliance, 4),
                        "coverage_score": round(coverage_score, 4),
                        "empty_match_rate": empty_match_rate,
                        "error_rate": round(error_rate, 4),
                        "latency_ms_avg": latency_avg,
                        "latency_ms_p95": latency_p95,
                        "latency_ms_max": latency_max,
                        "cross_run_structural_diff": round(_safe_mean(structural_variance, default=0.0) or 0.0, 4),
                        "forbidden_fields_present": forbidden_hits,
                        "blind": blind_summary,
                        "negative_probes": negative_probe_results,
                        "db_checks": {
                            "symbol_checks": symbol_checks,
                            "dependency_checks": dependency_checks,
                            "dependency_pairs_checked": dep_total,
                            "dependency_pairs_invalid": dep_bad,
                        },
                        "source_assessment": {
                            "code_terms_checked": sem_total,
                            "code_terms_matched": sem_hits,
                            "direct_span_checks": direct_span_checks,
                            "direct_span_matches": direct_span_hits,
                            "methods_used": sorted(
                                {
                                    direct_method_by_entity.get(entity.structural_id, "unknown")
                                    for _, _, entity in [runs[0] for runs in by_invocation.values() if runs]
                                    if entity is not None
                                }
                            ),
                            "parser_failures": ctx.ts_failures,
                            "ignored_files": ctx.ts_ignored_files,
                        },
                        "contract": contract,
                        "contract_validation": {
                            "missing_required_paths": sorted(missing_paths),
                            "unknown_payload_keys": unknown_payload_keys,
                            "type_mismatches": sorted(type_mismatches),
                            "invariant_failures": sorted(invariant_failures),
                        },
                        "errors_total": len(errors),
                        "errors_sample": errors[:20],
                    }
                    reducer_results[reducer_id] = metrics

    return EvalOutput(
        reducer_results=reducer_results,
        coherence_store=coherence_store,
        blind_rates_by_language=blind_rates_by_language,
        blind_rates_by_kind=blind_rates_by_kind,
        hash_appendix=hash_appendix,
        calls_used=calls_used,
        invocations_total=invocations_total,
        invocation_errors=invocation_errors,
    )


def _render_markdown_report(
    *,
    result: dict[str, Any],
    reducer_results: dict[str, dict[str, Any]],
    sampled: list[Entity],
    calls_used: int,
    snapshot_id: str,
    args: argparse.Namespace,
    reducer_catalog: list[dict[str, Any]],
    baseline_comparison: dict[str, Any] | None,
    sciona_version: str | None,
    evaluator_sha1: str | None,
    ts_version: str | None,
    ts_lang_version: str | None,
) -> str:
    lines: list[str] = []
    lines.append("# Reducer Quality Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {result['timestamp_utc']}")
    lines.append(f"Snapshot: `{snapshot_id}`")
    lines.append(f"Sample size (`--nodes`): `{args.nodes}`")
    lines.append(f"Runs per invocation: `{args.runs}`")
    lines.append(f"Calls used: `{calls_used}`")
    lines.append(f"Reducers discovered via SCIONA: `{len(reducer_catalog)}`")
    lines.append(f"Languages in sample: {', '.join(result['languages_in_sample']) or 'none'}")
    lines.append(f"DB consistency score: `{result['db_consistency_score']:.4f}`")
    if sciona_version:
        lines.append(f"SCIONA version: `{sciona_version}`")
    if evaluator_sha1:
        lines.append(f"Evaluator SHA1: `{evaluator_sha1}`")
    if ts_version:
        lines.append(f"Tree-sitter version: `{ts_version}`")
    if ts_lang_version:
        lines.append(f"Tree-sitter-languages version: `{ts_lang_version}`")
    lines.append(
        "Ground truth hierarchy: "
        + " > ".join(result["ground_truth_hierarchy"])
    )
    if result["contract_scope_mismatches"]:
        lines.append("Contract scope mismatches detected.")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    for item in _build_executive_summary(
        reducer_results=reducer_results,
        sampled=sampled,
        calls_used=calls_used,
    ):
        lines.append(f"- {item}")
    lines.append(
        "- Secondary signals: `identifier_overlap` measures evidence-term overlap between "
        "payload identifiers and direct-code terms (not a recall metric); `unknown_id_qname_rate` "
        "penalizes only categories enabled by contract policy (out_of_scope/out_of_sample may be allowed)."
    )
    lines.append("")
    lines.append("## Copilot Overall Summary")
    lines.append("")
    lines.append("TO_BE_FILLED_BY_COPILOT")
    lines.append("")
    lines.append("## Blind Summary")
    lines.append("")
    for item in result["blind_summary"]:
        lines.append(f"- {item}")
    if result["blind_summary_by_language"]:
        lines.append("")
        lines.append("## Blind Summary By Language")
        lines.append("")
        for lang, summary in result["blind_summary_by_language"].items():
            lines.append(
                f"- `{lang}`: "
                f"avg_blind_error_rate=`{summary['blind_error_rate']}`, "
                f"avg_content_hash_match=`{summary['content_hash_match_rate']}`, "
                f"hash_diagnostics=`{summary.get('hash_diagnostics_total', 0)}`"
            )
    if result["blind_summary_by_kind"]:
        lines.append("")
        lines.append("## Blind Summary By Kind")
        lines.append("")
        for kind, summary in result["blind_summary_by_kind"].items():
            lines.append(
                f"- `{kind}`: "
                f"avg_blind_error_rate=`{summary['blind_error_rate']}`, "
                f"avg_content_hash_match=`{summary['content_hash_match_rate']}`, "
                f"hash_diagnostics=`{summary.get('hash_diagnostics_total', 0)}`"
            )
    lines.append("")
    lines.append("## Consolidated Summary")
    lines.append("")
    for item in result["consolidated_summary"]:
        lines.append(f"- {item}")
    lines.append("- Full details are available in the JSON report.")
    if baseline_comparison:
        lines.append("")
        lines.append("## Baseline Comparison")
        lines.append("")
        for item in baseline_comparison.get("summary", []):
            lines.append(f"- {item}")
        regressions = baseline_comparison.get("regressions", [])
        if regressions:
            for item in regressions:
                lines.append(f"- Regression: {item}")
        else:
            lines.append("- No regressions detected under current thresholds.")
    if result.get("coherence_checks"):
        lines.append("")
        lines.append("## Coherence Checks")
        lines.append("")
        for name, payload in result["coherence_checks"].items():
            parts = ", ".join(f"{key}=`{value}`" for key, value in payload.items())
            lines.append(f"- `{name}`: {parts}")
    lines.append("")
    lines.append("## Sampled Entities")
    lines.append("")
    lines.append("Population by language:")
    for lang, count in sorted(result["population_by_language"].items()):
        lines.append(f"- `{lang}`: `{count}`")
    lines.append("Population by kind:")
    for kind, count in sorted(result["population_by_kind"].items()):
        lines.append(f"- `{kind}`: `{count}`")
    lines.append("")
    lines.append("## Per-Reducer Summary")
    lines.append("")
    lines.append(
        "Metrics key: `structural_accuracy`, `schema_compliance_score`, `coverage_score`, "
        "`determinism_score`, secondary=`identifier_overlap` (evidence-term overlap), "
        "`unknown_id_qname_rate` (out_of_scope/out_of_sample/unresolved_in_scope/"
        "resolution_failure), `omission_rate`."
    )
    lines.append("")
    for reducer_id in sorted(reducer_results):
        row = reducer_results[reducer_id]
        if "error" in row:
            lines.append(f"- `{reducer_id}`: error=`{row['error']}`")
            continue
        hash_diag_count = row.get("blind", {}).get("hash_diagnostics_total", 0) or 0
        extra = ""
        if row.get("empty_match_rate") is not None:
            extra += f", empty_match_rate=`{row['empty_match_rate']}`"
        extra += f", ordering_instability_rate=`{row.get('ordering_instability_rate', 0.0)}`"
        if row.get("latency_ms_avg") is not None:
            extra += f", latency_ms_avg=`{row['latency_ms_avg']}`"
        if row.get("latency_ms_p95") is not None:
            extra += f", latency_ms_p95=`{row['latency_ms_p95']}`"
        if row.get("latency_ms_max") is not None:
            extra += f", latency_ms_max=`{row['latency_ms_max']}`"
        extra += f", hash_diagnostics=`{hash_diag_count}`"
        lines.append(
            f"- `{reducer_id}`: "
            f"type=`{row.get('reducer_type', 'unknown')}`, "
            f"structural_accuracy=`{_fmt_metric(row.get('structural_accuracy'))}`, "
            f"schema_compliance_score=`{row.get('schema_compliance_score', 1.0)}`, "
            f"coverage_score=`{row.get('coverage_score', 0.0)}`, "
            f"determinism_score=`{row['determinism_score']}`, "
            f"identifier_overlap=`{_fmt_metric(row.get('identifier_overlap'))}`, "
            f"unknown_id_qname_rate=`{_fmt_metric(row.get('unknown_id_qname_rate'))}` "
            f"(out_of_scope=`{_fmt_metric(row.get('unknown_id_qname_out_of_scope_rate'))}`, "
            f"out_of_sample=`{_fmt_metric(row.get('unknown_id_qname_out_of_sample_rate'))}`, "
            f"unresolved_in_scope=`{_fmt_metric(row.get('unknown_id_qname_unresolved_in_scope_rate'))}`, "
            f"resolution_failure=`{_fmt_metric(row.get('unknown_id_qname_resolution_failure_rate'))}`), "
            f"omission_rate=`{row['omission_rate']}`"
            f"{extra}"
        )
    lines.append("")

    lines.append("## Contract Consistency")
    lines.append("")
    for reducer_id, summary in result["contract_consistency"].items():
        lines.append(
            f"- `{reducer_id}`: "
            f"missing_required_paths=`{len(summary.get('missing_required_paths', []))}`, "
            f"unknown_payload_keys=`{len(summary.get('unknown_payload_keys', []))}`, "
            f"type_mismatches=`{len(summary.get('type_mismatches', []))}`, "
            f"invariant_failures=`{len(summary.get('invariant_failures', []))}`, "
            f"forbidden_fields_present=`{summary.get('forbidden_fields_present', 0)}`"
        )
    if result["contract_scope_mismatches"]:
        lines.append("")
        lines.append("## Contract Scope Mismatches")
        lines.append("")
        for item in result["contract_scope_mismatches"]:
            lines.append(
                f"- `{item['reducer_id']}`: contract=`{item['contract_scope']}`, catalog=`{item['catalog_scope']}`"
            )

    if result.get("hash_diagnostics_appendix"):
        lines.append("")
        lines.append("## Hash Diagnostics Appendix")
        lines.append("")
        for diag in result["hash_diagnostics_appendix"]:
            reducer_id = diag.get("reducer_id")
            entity_id = diag.get("entity_id")
            file_path = diag.get("file_path")
            line_span = diag.get("line_span")
            lines.append(
                f"- reducer=`{reducer_id}` entity=`{entity_id}` "
                f"file=`{file_path}` span=`{line_span}`"
            )
    return "\n".join(lines) + "\n"


def _sanitize_run_parameters(run_parameters: dict[str, Any]) -> dict[str, Any]:
    repo_root = run_parameters.get("repo_root")
    if not isinstance(repo_root, str) or not repo_root:
        return run_parameters
    repo_root_path = Path(repo_root)
    sanitized = dict(run_parameters)
    sanitized["repo_root"] = "repo_root/"
    for key in ("contracts", "out_json", "out_md", "baseline_json", "regression_thresholds"):
        value = sanitized.get(key)
        if not isinstance(value, str):
            continue
        try:
            sanitized[key] = _normalize_report_path(repo_root_path, value)
        except Exception:
            continue
    return sanitized


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()

    out_json, out_md, report_prefix = _resolve_output_paths(args, repo_root)

    effective_db_path, effective_artifact_path, readonly_core, readonly_artifact = _prepare_db_paths(
        args, repo_root
    )
    artifact_path = get_artifact_db_path(repo_root)

    if args.mode == "full":
        args.nodes = max(args.nodes, 24)
        args.runs = max(args.runs, 10)

    reducers = get_reducers()
    reducer_ids = sorted(reducers.keys())
    requested = [item.strip() for item in args.reducers.split(",") if item.strip()]
    if requested:
        unknown = sorted(set(requested) - set(reducer_ids))
        if unknown:
            raise SystemExit(f"Unknown reducers requested: {', '.join(unknown)}")
        reducer_ids = [rid for rid in reducer_ids if rid in set(requested)]
    # SCIONA-first reducer inspection metadata.
    reducer_catalog = reducers_pipeline.list_entries(repo_root=repo_root)
    catalog_scopes = {entry["reducer_id"]: entry["scope"] for entry in reducer_catalog}
    contracts_path = args.contracts
    if not contracts_path.is_absolute():
        contracts_path = (SCRIPT_DIR / contracts_path).resolve()
    contracts = _load_contracts(contracts_path)
    contract_scope_mismatches = []
    for reducer_id, spec in contracts.items():
        contract_scope = spec.get("scope")
        catalog_scope = catalog_scopes.get(reducer_id)
        if catalog_scope and contract_scope and catalog_scope != contract_scope:
            contract_scope_mismatches.append(
                {
                    "reducer_id": reducer_id,
                    "contract_scope": contract_scope,
                    "catalog_scope": catalog_scope,
                }
            )

    snapshot_id, effective_db_path, readonly_core = _resolve_snapshot_id(
        effective_db_path, repo_root, readonly_core
    )
    ctx = EvalContext()
    sampling = _prepare_sampling(repo_root, effective_db_path, snapshot_id, args, ctx)
    gt = _collect_ground_truth(effective_db_path, effective_artifact_path, artifact_path)

    eval_output = _evaluate_reducers(
        repo_root=repo_root,
        effective_db_path=effective_db_path,
        effective_artifact_path=effective_artifact_path,
        artifact_path=artifact_path,
        readonly_core=readonly_core,
        readonly_artifact=readonly_artifact,
        snapshot_id=snapshot_id,
        reducer_ids=reducer_ids,
        sampled=sampling.sampled,
        query_terms=sampling.query_terms,
        contracts=contracts,
        ctx=ctx,
        args=args,
        gt=gt,
        sampled_ids=sampling.sampled_ids,
        sampled_qnames=sampling.sampled_qnames,
        direct_terms=sampling.direct_terms,
        direct_method_by_entity=sampling.direct_method_by_entity,
    )

    coherence_results = _coherence_checks(eval_output.coherence_store)
    sciona_version = _get_sciona_version()
    evaluator_sha1 = _file_sha1(Path(__file__).resolve())
    ts_version = _get_pkg_version("tree_sitter")
    ts_lang_version = _get_pkg_version("tree_sitter_languages")
    thresholds = _load_thresholds(args.regression_thresholds)
    baseline_comparison: dict[str, Any] | None = None
    if args.baseline_json is not None and args.baseline_json.exists():
        try:
            baseline_data = json.loads(args.baseline_json.read_text(encoding="utf-8"))
        except Exception:
            baseline_data = None
        if isinstance(baseline_data, dict):
            baseline_comparison = _baseline_diff(
                current={"reducers": eval_output.reducer_results},
                baseline=baseline_data,
                thresholds=thresholds,
            )
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot_id,
        "ground_truth_hierarchy": [
            "direct_code",
            "sciona_db",
            "reducer_output",
        ],
        "run_parameters": {
            "repo_root": str(repo_root),
            "nodes": args.nodes,
            "runs": args.runs,
            "seed": args.seed,
            "reducers_requested": requested,
            "contracts": str(contracts_path),
            "out_json": str(out_json),
            "out_md": str(out_md),
            "baseline_json": str(args.baseline_json) if args.baseline_json else None,
            "regression_thresholds": str(args.regression_thresholds) if args.regression_thresholds else None,
        },
        "seed": args.seed,
        "runs_per_invocation": args.runs,
        "calls_used": eval_output.calls_used,
        "invocations_total": eval_output.invocations_total,
        "invocation_errors": eval_output.invocation_errors,
        "reducers_requested": requested,
        "db_consistency_score": _db_consistency(gt.gt_ids, gt.art_nodes),
        "db_consistency_details": {
            "core_structural_ids": len(gt.gt_ids),
            "artifact_node_ids": len(gt.art_nodes),
            "intersection": len(gt.gt_ids & gt.art_nodes),
        },
        "sampled_nodes": args.nodes,
        "languages_in_sample": sorted({e.language for e in sampling.sampled}),
        "population_by_language": dict(sampling.population_by_language),
        "population_by_kind": dict(sampling.population_by_kind),
        "sampled_entities": [e.__dict__ for e in sampling.sampled],
        "llm_config": {"temperature": 0, "top_p": 1, "seed": args.seed},
        "reducer_catalog": reducer_catalog,
        "reducers": eval_output.reducer_results,
        "blind_summary": _build_blind_summary(eval_output.reducer_results),
        "blind_summary_by_language": {
            lang: _aggregate_blind(entries) for lang, entries in sorted(eval_output.blind_rates_by_language.items())
        },
        "blind_summary_by_kind": {
            kind: _aggregate_blind(entries) for kind, entries in sorted(eval_output.blind_rates_by_kind.items())
        },
        "consolidated_summary": _build_consolidated_summary(eval_output.reducer_results),
        "hash_diagnostics_appendix": eval_output.hash_appendix,
        "toolchain": {
            "sciona_version": sciona_version,
            "evaluator_sha1": evaluator_sha1,
            "tree_sitter_version": ts_version,
            "tree_sitter_languages_version": ts_lang_version,
        },
        "baseline_comparison": baseline_comparison,
        "contract_scope_mismatches": contract_scope_mismatches,
        "contract_consistency": {
            reducer_id: {
                "missing_required_paths": row.get("contract_validation", {}).get(
                    "missing_required_paths", []
                ),
                "unknown_payload_keys": row.get("contract_validation", {}).get(
                    "unknown_payload_keys", []
                ),
                "type_mismatches": row.get("contract_validation", {}).get(
                    "type_mismatches", []
                ),
                "invariant_failures": row.get("contract_validation", {}).get(
                    "invariant_failures", []
                ),
                "forbidden_fields_present": row.get("forbidden_fields_present", 0),
            }
            for reducer_id, row in eval_output.reducer_results.items()
            if "error" not in row
        },
        "coherence_checks": coherence_results,
        "notes": [
            "Reducer-specific invocation and validation enabled.",
            "Source reducers (concatenated_source/callable_source) skip unknown-id/qname checks.",
            "Direct code assessment uses tree-sitter when available, with AST fallback.",
            "Coherence checks normalize callsite_index by excluding the focal callable id.",
            "Unknown-id/qname penalties follow contract policy; out-of-scope/out-of-sample may be allowed.",
            "Identifier overlap is evidence-term overlap and is computed only when enabled by contract policy.",
            "Content-hash mismatches include span diagnostics in blind results.",
            "Unknown-id/qname sub-rates include out-of-scope, out-of-sample, unresolved-in-scope, and resolution-failure categories.",
            "Coverage for symbol reducers treats empty match lists as valid payloads.",
            "Unknown-id/qname breakdown reports all categories; penalization is policy-driven.",
            "Ordering instability is detected when outputs differ only by list/map ordering.",
            "cross_run_structural_diff is an alias of structural_variance for reporting continuity.",
        ],
    }
    result["run_parameters"] = _sanitize_run_parameters(result["run_parameters"])
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    out_md.write_text(
        _render_markdown_report(
            result=result,
            reducer_results=eval_output.reducer_results,
            sampled=sampling.sampled,
            calls_used=eval_output.calls_used,
            snapshot_id=snapshot_id,
            args=args,
            reducer_catalog=reducer_catalog,
            baseline_comparison=baseline_comparison,
            sciona_version=sciona_version,
            evaluator_sha1=evaluator_sha1,
            ts_version=ts_version,
            ts_lang_version=ts_lang_version,
        ),
        encoding="utf-8",
    )
    print(f"{report_prefix}Wrote: {out_json}")
    print(f"{report_prefix}Wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
