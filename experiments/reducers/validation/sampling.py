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
            entities.append(
                Entity(
                    structural_id=entry.get("structural_id") or "",
                    qualified_name=qname,
                    kind="function",
                    language=language,
                    file_path=file_path or "",
                    module_qualified_name=module_name,
                    start_line=None,
                    end_line=None,
                )
            )
        for entry in overview.get("methods", []) or []:
            qname = entry.get("qualified_name")
            if not qname:
                continue
            entities.append(
                Entity(
                    structural_id=entry.get("structural_id") or "",
                    qualified_name=qname,
                    kind="method",
                    language=language,
                    file_path=file_path or "",
                    module_qualified_name=module_name,
                    start_line=None,
                    end_line=None,
                )
            )
    return entities


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
    for entity in entities:
        key = _group_key(entity)
        grouped.setdefault(key, []).append(entity)

    rng = random.Random(seed)
    for bucket in grouped.values():
        rng.shuffle(bucket)

    group_keys = list(grouped.keys())
    rng.shuffle(group_keys)

    sampled: list[Entity] = []
    used_ids: set[str] = set()
    idx = 0
    while len(sampled) < total_nodes and group_keys:
        key = group_keys[idx % len(group_keys)]
        idx += 1
        bucket = grouped.get(key, [])
        while bucket and bucket[-1].structural_id in used_ids:
            bucket.pop()
        if not bucket:
            grouped.pop(key, None)
            group_keys = list(grouped.keys())
            if not group_keys:
                break
            continue
        choice = bucket.pop()
        used_ids.add(choice.structural_id)
        sampled.append(choice)

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
