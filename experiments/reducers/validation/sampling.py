# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import random
import sqlite3
import re

from .config import bucket_value, CALL_DENSITY_BUCKETS, DEPTH_BUCKETS, LOC_BUCKETS


@dataclass(frozen=True)
class Entity:
    structural_id: str
    qualified_name: str
    kind: str
    language: str
    file_path: str
    start_line: int | None
    end_line: int | None

    @property
    def depth(self) -> int:
        return self.qualified_name.count(".")


@dataclass(frozen=True)
class SamplingResult:
    sampled: list[Entity]
    population_by_language: Dict[str, int]
    population_by_kind: Dict[str, int]
    strata_counts: Dict[str, int]


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_entities(repo_root: Path, db_path: Path) -> list[Entity]:
    conn = _open_readonly(db_path)
    try:
        rows = conn.execute(
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
            WHERE ni.snapshot_id = (
                SELECT snapshot_id
                FROM snapshots
                WHERE is_committed = 1
                ORDER BY COALESCE(git_commit_time, created_at) DESC, snapshot_id DESC
                LIMIT 1
            )
              AND sn.node_type IN ('module', 'class', 'function', 'method')
            """
        ).fetchall()
    finally:
        conn.close()

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


def _estimate_loc(entity: Entity, repo_root: Path) -> int:
    if entity.start_line and entity.end_line and entity.end_line >= entity.start_line:
        return max(1, entity.end_line - entity.start_line + 1)
    try:
        return sum(1 for _ in (repo_root / entity.file_path).open("r", encoding="utf-8"))
    except OSError:
        return 1


def _count_call_like_tokens(text: str) -> int:
    return len(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(", text))


def _estimate_call_density(entity: Entity, repo_root: Path) -> float:
    try:
        lines = (repo_root / entity.file_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0.0
    if not lines:
        return 0.0
    start = max((entity.start_line or 1) - 1, 0)
    end = min(entity.end_line or len(lines), len(lines))
    snippet = "\n".join(lines[start:end])
    calls = _count_call_like_tokens(snippet)
    loc = max(1, end - start)
    return calls / loc


def _bucket_key(entity: Entity, repo_root: Path) -> Tuple[str, str, str]:
    loc = _estimate_loc(entity, repo_root)
    call_density = _estimate_call_density(entity, repo_root)
    depth = entity.depth
    loc_bucket = bucket_value(loc, LOC_BUCKETS)
    call_bucket = bucket_value(call_density, CALL_DENSITY_BUCKETS)
    depth_bucket = bucket_value(depth, DEPTH_BUCKETS)
    return loc_bucket, call_bucket, depth_bucket


def _group_key(entity: Entity, repo_root: Path) -> Tuple[str, str, str, str, str]:
    loc_bucket, call_bucket, depth_bucket = _bucket_key(entity, repo_root)
    return (entity.language, entity.kind, loc_bucket, call_bucket, depth_bucket)


def sample_entities(
    entities: Iterable[Entity],
    repo_root: Path,
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
        key = _group_key(entity, repo_root)
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
        key = _group_key(entity, repo_root)
        label = "/".join(key)
        strata_counts[label] = strata_counts.get(label, 0) + 1

    return SamplingResult(
        sampled=sampled,
        population_by_language=population_by_language,
        population_by_kind=population_by_kind,
        strata_counts=strata_counts,
    )
