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
    assert set(payload["allowed_non_accepted_gate_reasons"]) == set(
        in_repo_static_gate.ALLOWED_NON_ACCEPTED_GATE_REASONS
    )


def test_local_binding_resolution_contract_json_shape() -> None:
    payload = json.loads(
        Path(
            "src/sciona/code_analysis/languages/common/contracts/local_binding_resolution.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["binding_precedence"] == [
        "shared_tree_sitter_binding_facts",
        "per_language_deepening",
        "minimal_custom_extension",
    ]
    assert "direct_import_symbol" in payload["allowed_binding_kinds"]
    assert "namespace_alias" in payload["allowed_binding_kinds"]
    assert "syntax_local_import" in payload["allowed_binding_evidence"]
    assert "syntax_local_receiver_chain" in payload["allowed_binding_evidence"]
    assert "dynamic_import" in payload["forbidden_dynamic_shapes"]
    assert "computed_member_access" in payload["forbidden_dynamic_shapes"]
    assert "unique_target_only" in payload["acceptance_requirements"]
    assert "no_runtime_inference" in payload["acceptance_requirements"]
