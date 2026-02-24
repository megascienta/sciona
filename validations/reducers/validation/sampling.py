# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple
import random

from .config import bucket_value, CALL_DENSITY_BUCKETS, DEPTH_BUCKETS, LOC_BUCKETS


@dataclass
class Entity:
    structural_id: str
    qualified_name: str
    kind: str
    language: str
    file_path: str
    module_qualified_name: str
    start_line: int | None
    end_line: int | None
    call_edge_count: int | None = None

    @property
    def depth(self) -> int:
        return self.qualified_name.count(".")


@dataclass(frozen=True)
class SamplingResult:
    sampled: list[Entity]
    population_by_language: Dict[str, int]
    population_by_kind: Dict[str, int]
    strata_counts: Dict[str, int]


def build_entities_from_structural_index(
    structural_index: dict,
    module_overviews: Dict[str, dict],
) -> list[Entity]:
    entities: list[Entity] = []
    module_file_map: Dict[str, str] = {}
    for entry in structural_index.get("files", {}).get("entries", []):
        module_name = entry.get("module_qualified_name")
        path = entry.get("path")
        if module_name and path and module_name not in module_file_map:
            module_file_map[module_name] = path

    for entry in structural_index.get("modules", {}).get("entries", []):
        module_name = entry.get("module_qualified_name")
        if not module_name:
            continue
        overview = module_overviews.get(module_name, {})
        file_path = overview.get("file_path") or module_file_map.get(module_name, "")
        entities.append(
            Entity(
                structural_id=overview.get("module_structural_id") or "",
                qualified_name=module_name,
                kind="module",
                language=entry.get("language") or overview.get("language") or "",
                file_path=file_path or "",
                module_qualified_name=module_name,
                start_line=(overview.get("line_span") or [None, None])[0],
                end_line=(overview.get("line_span") or [None, None])[1],
            )
        )

    for entry in structural_index.get("classes", {}).get("entries", []):
        qname = entry.get("qualified_name")
        if not qname:
            continue
        line_span = entry.get("line_span") or [None, None]
        module_name = entry.get("module_qualified_name") or ""
        entities.append(
            Entity(
                structural_id=entry.get("structural_id") or "",
                qualified_name=qname,
                kind="class",
                language=entry.get("language") or "",
                file_path=entry.get("file_path") or "",
                module_qualified_name=module_name,
                start_line=line_span[0],
                end_line=line_span[1],
            )
        )

    for module_name, overview in module_overviews.items():
        language = overview.get("language") or ""
        file_path = overview.get("file_path") or module_file_map.get(module_name, "")
        for entry in overview.get("functions", []) or []:
            qname = entry.get("qualified_name")
            if not qname:
                continue
            module_qname = _module_from_qualified_name("function", qname)
            entities.append(
                Entity(
                    structural_id=entry.get("structural_id") or "",
                    qualified_name=qname,
                    kind="function",
                    language=language,
                    file_path=file_path or "",
                    module_qualified_name=module_qname,
                    start_line=None,
                    end_line=None,
                )
            )
        for entry in overview.get("methods", []) or []:
            qname = entry.get("qualified_name")
            if not qname:
                continue
            module_qname = _module_from_qualified_name("method", qname)
            entities.append(
                Entity(
                    structural_id=entry.get("structural_id") or "",
                    qualified_name=qname,
                    kind="method",
                    language=language,
                    file_path=file_path or "",
                    module_qualified_name=module_qname,
                    start_line=None,
                    end_line=None,
                )
            )
    return entities


def build_entities_from_db(nodes: Iterable[dict]) -> list[Entity]:
    entities: list[Entity] = []
    for entry in nodes:
        qname = entry.get("qualified_name")
        kind = entry.get("node_type") or entry.get("node_kind")
        if not qname or not kind:
            continue
        language = entry.get("language") or ""
        file_path = entry.get("file_path") or ""
        module_name = _module_from_qualified_name(kind, qname)
        entities.append(
            Entity(
                structural_id=entry.get("structural_id") or "",
                qualified_name=qname,
                kind=kind,
                language=language,
                file_path=file_path,
                module_qualified_name=module_name,
                start_line=entry.get("start_line"),
                end_line=entry.get("end_line"),
            )
        )
    return entities


def _module_from_qualified_name(kind: str, qualified_name: str) -> str:
    parts = qualified_name.split(".")
    if kind == "method":
        if len(parts) > 2:
            return ".".join(parts[:-2])
        if len(parts) > 1:
            return ".".join(parts[:-1])
        return qualified_name
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return qualified_name


def _estimate_loc(entity: Entity) -> int:
    if entity.start_line and entity.end_line and entity.end_line >= entity.start_line:
        return max(1, entity.end_line - entity.start_line + 1)
    return 1


def _estimate_call_density(entity: Entity) -> float:
    count = entity.call_edge_count or 0
    loc = _estimate_loc(entity)
    return count / max(1, loc)


def _bucket_key(entity: Entity) -> Tuple[str, str, str]:
    loc = _estimate_loc(entity)
    call_density = _estimate_call_density(entity)
    depth = entity.depth
    loc_bucket = bucket_value(loc, LOC_BUCKETS)
    call_bucket = bucket_value(call_density, CALL_DENSITY_BUCKETS)
    depth_bucket = bucket_value(depth, DEPTH_BUCKETS)
    return loc_bucket, call_bucket, depth_bucket


def _group_key(entity: Entity) -> Tuple[str, str, str, str, str]:
    loc_bucket, call_bucket, depth_bucket = _bucket_key(entity)
    return (entity.language, entity.kind, loc_bucket, call_bucket, depth_bucket)


def sample_entities(
    entities: Iterable[Entity],
    total_nodes: int,
    seed: int,
) -> SamplingResult:
    entities = list(entities)
    population_by_language: Dict[str, int] = {}
    population_by_kind: Dict[str, int] = {}
    for entity in entities:
        population_by_language[entity.language] = population_by_language.get(entity.language, 0) + 1
        population_by_kind[entity.kind] = population_by_kind.get(entity.kind, 0) + 1

    grouped: Dict[Tuple[str, str, str, str, str], List[Entity]] = {}
    grouped_by_pair: Dict[Tuple[str, str], Dict[Tuple[str, str, str], List[Entity]]] = {}
    for entity in entities:
        key = _group_key(entity)
        grouped.setdefault(key, []).append(entity)
        pair_key = (entity.language, entity.kind)
        grouped_by_pair.setdefault(pair_key, {}).setdefault(key[2:], []).append(entity)

    rng = random.Random(seed)
    for bucket in grouped.values():
        rng.shuffle(bucket)
    for pair_buckets in grouped_by_pair.values():
        for bucket in pair_buckets.values():
            rng.shuffle(bucket)

    sampled: list[Entity] = []
    used_ids: set[str] = set()
    pair_keys = list(grouped_by_pair.keys())
    rng.shuffle(pair_keys)
    quotas: Dict[Tuple[str, str], int] = {}
    if pair_keys:
        base = total_nodes // len(pair_keys)
        remainder = total_nodes % len(pair_keys)
        for idx, key in enumerate(pair_keys):
            quotas[key] = base + (1 if idx < remainder else 0)

    def _draw_from_pair(pair_key: Tuple[str, str], limit: int) -> list[Entity]:
        selected: list[Entity] = []
        buckets = grouped_by_pair.get(pair_key, {})
        stratum_keys = list(buckets.keys())
        rng.shuffle(stratum_keys)
        if not stratum_keys:
            return selected
        idx = 0
        while len(selected) < limit and stratum_keys:
            stratum = stratum_keys[idx % len(stratum_keys)]
            idx += 1
            bucket = buckets.get(stratum, [])
            while bucket and bucket[-1].structural_id in used_ids:
                bucket.pop()
            if not bucket:
                buckets.pop(stratum, None)
                stratum_keys = list(buckets.keys())
                if not stratum_keys:
                    break
                continue
            choice = bucket.pop()
            used_ids.add(choice.structural_id)
            selected.append(choice)
        return selected

    for pair_key in pair_keys:
        quota = quotas.get(pair_key, 0)
        if quota <= 0:
            continue
        sampled.extend(_draw_from_pair(pair_key, quota))

    if len(sampled) < total_nodes:
        remaining = total_nodes - len(sampled)
        all_group_keys = list(grouped.keys())
        rng.shuffle(all_group_keys)
        idx = 0
        while remaining > 0 and all_group_keys:
            key = all_group_keys[idx % len(all_group_keys)]
            idx += 1
            bucket = grouped.get(key, [])
            while bucket and bucket[-1].structural_id in used_ids:
                bucket.pop()
            if not bucket:
                grouped.pop(key, None)
                all_group_keys = list(grouped.keys())
                if not all_group_keys:
                    break
                continue
            choice = bucket.pop()
            used_ids.add(choice.structural_id)
            sampled.append(choice)
            remaining -= 1

    strata_counts: Dict[str, int] = {}
    for entity in sampled:
        key = _group_key(entity)
        label = "/".join(key)
        strata_counts[label] = strata_counts.get(label, 0) + 1

    return SamplingResult(
        sampled=sampled,
        population_by_language=population_by_language,
        population_by_kind=population_by_kind,
        strata_counts=strata_counts,
    )
