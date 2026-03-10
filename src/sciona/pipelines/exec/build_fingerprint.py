# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Deterministic build-fingerprint cache for rebuild fast-path checks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from ...code_analysis.languages.common.support.parity_contract import PARITY_CONTRACT_VERSION
from ...data_storage.artifact_db.schema import SCHEMA_STATEMENTS as ARTIFACT_SCHEMA_STATEMENTS
from ...data_storage.core_db.schema import SCHEMA_STATEMENTS as CORE_SCHEMA_STATEMENTS
from ...runtime.common import constants as runtime_constants
from ...runtime.config.io import load_raw_config
from ...runtime.common.time import utc_now
from ..domain.policies import BuildPolicy
from ..domain.repository import RepoState

_CACHE_FILENAME = ".build_fingerprint.json"


@dataclass(frozen=True)
class BuildFingerprint:
    fingerprint_hash: str
    payload: dict[str, Any]


def compute_build_fingerprint(
    *,
    repo_state: RepoState,
    policy: BuildPolicy,
    source: str,
    git_commit_sha: str,
) -> BuildFingerprint:
    payload = {
        "git_commit_sha": git_commit_sha,
        "source": source,
        "config": _normalized_runtime_config(repo_state.repo_root),
        "analysis_languages": {
            name: bool(settings.enabled)
            for name, settings in sorted(policy.analysis.languages.items())
        },
        "artifacts": {
            "refresh_artifacts": bool(policy.artifacts.refresh_artifacts),
            "refresh_calls": bool(policy.artifacts.refresh_calls),
            "force_rebuild": bool(policy.force_rebuild),
        },
        "versions": {
            "tool_version": runtime_constants.TOOL_VERSION,
            "schema_version": runtime_constants.SCHEMA_VERSION,
            "parity_contract_version": PARITY_CONTRACT_VERSION,
            "core_schema_hash": _schema_hash(CORE_SCHEMA_STATEMENTS),
            "artifact_schema_hash": _schema_hash(ARTIFACT_SCHEMA_STATEMENTS),
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return BuildFingerprint(
        fingerprint_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        payload=payload,
    )


def load_fingerprint_cache(repo_state: RepoState) -> dict[str, Any] | None:
    path = _cache_path(repo_state.sciona_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def write_fingerprint_cache(
    *,
    repo_state: RepoState,
    fingerprint: BuildFingerprint,
    structural_hash: str,
    result_payload: dict[str, Any],
) -> None:
    payload = {
        "recorded_at": utc_now(),
        "fingerprint_hash": fingerprint.fingerprint_hash,
        "fingerprint_payload": fingerprint.payload,
        "snapshot_id": result_payload.get("snapshot_id"),
        "structural_hash": structural_hash,
        "build_result": result_payload,
    }
    path = _cache_path(repo_state.sciona_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_cached_build_result_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    result_payload = payload.get("build_result")
    if not isinstance(result_payload, dict):
        return None
    return result_payload


def _cache_path(sciona_dir: Path) -> Path:
    return sciona_dir / _CACHE_FILENAME


def _schema_hash(statements: list[str]) -> str:
    joined = "\n".join(part.strip() for part in statements if part)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _normalized_runtime_config(repo_root: Path) -> dict[str, Any]:
    raw = load_raw_config(repo_root)
    return json.loads(json.dumps(raw, sort_keys=True))


__all__ = [
    "BuildFingerprint",
    "compute_build_fingerprint",
    "load_cached_build_result_payload",
    "load_fingerprint_cache",
    "write_fingerprint_cache",
]
