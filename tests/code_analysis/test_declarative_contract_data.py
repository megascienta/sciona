# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from sciona.code_analysis.artifacts import in_repo_static_gate
from sciona.code_analysis.languages.common.support.parity_contract import (
    build_parity_contract,
)
from sciona.code_analysis.languages.common.support.walker_capabilities import (
    build_walker_capabilities,
)


def test_walker_capabilities_contract_json_matches_loader() -> None:
    payload = json.loads(
        Path(
            "src/sciona/code_analysis/languages/common/contracts/walker_capabilities.json"
        ).read_text(encoding="utf-8")
    )
    assert payload == build_walker_capabilities()


def test_parity_contract_json_matches_loader() -> None:
    payload = json.loads(
        Path(
            "src/sciona/code_analysis/languages/common/contracts/parity_contract.json"
        ).read_text(encoding="utf-8")
    )
    payload["version"] = build_parity_contract()["version"]
    assert payload == build_parity_contract()


def test_in_repo_static_gate_json_matches_loader() -> None:
    payload = json.loads(
        Path(
            "src/sciona/code_analysis/languages/common/contracts/in_repo_static_gate.json"
        ).read_text(encoding="utf-8")
    )
    assert set(payload["allowed_callsite_provenance"]) == set(
        in_repo_static_gate.ALLOWED_CALLSITE_PROVENANCE
    )
    assert set(payload["allowed_callsite_drop_reasons"]) == set(
        in_repo_static_gate.ALLOWED_CALLSITE_DROP_REASONS
    )
    assert set(payload["allowed_pre_persist_filter_buckets"]) == set(
        in_repo_static_gate.ALLOWED_PRE_PERSIST_FILTER_BUCKETS
    )
