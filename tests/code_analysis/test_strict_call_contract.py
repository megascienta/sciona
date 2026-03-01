# SPDX-License-Identifier: MIT

from sciona.code_analysis.contracts import select_strict_call_candidate


def test_strict_call_contract_accepts_exact_qname() -> None:
    decision = select_strict_call_candidate(
        identifier="pkg.mod.Service.run",
        direct_candidates=["pkg.mod.Service.run"],
        fallback_candidates=[],
        caller_module="pkg.mod",
        module_lookup={"pkg.mod.Service.run": "pkg.mod"},
        import_targets={},
    )
    assert decision.accepted_candidate == "pkg.mod.Service.run"
    assert decision.accepted_provenance == "exact_qname"
    assert decision.dropped_reason is None


def test_strict_call_contract_rejects_unique_without_provenance() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=["other.pkg.Service.run"],
        caller_module="pkg.mod",
        module_lookup={"other.pkg.Service.run": "other.pkg"},
        import_targets={},
    )
    assert decision.accepted_candidate is None
    assert decision.dropped_reason == "unique_without_provenance"


def test_strict_call_contract_accepts_import_narrowed_from_ambiguous() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=["a.mod.S.run", "b.mod.S.run"],
        caller_module="a.mod",
        module_lookup={"a.mod.S.run": "a.mod", "b.mod.S.run": "b.mod"},
        import_targets={"a.mod": {"a.mod"}},
    )
    assert decision.accepted_candidate == "a.mod.S.run"
    assert decision.accepted_provenance == "import_narrowed"


def test_strict_call_contract_accepts_unique_import_scoped_candidate() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=["deps.mod.S.run"],
        caller_module="app.mod",
        module_lookup={"deps.mod.S.run": "deps.mod"},
        import_targets={"app.mod": {"deps.mod"}},
    )
    assert decision.accepted_candidate == "deps.mod.S.run"
    assert decision.accepted_provenance == "import_narrowed"


def test_strict_call_contract_accepts_unique_same_module_candidate() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=["app.mod.S.run"],
        caller_module="app.mod",
        module_lookup={"app.mod.S.run": "app.mod"},
        import_targets={},
    )
    assert decision.accepted_candidate == "app.mod.S.run"
    assert decision.accepted_provenance == "module_scoped"
    assert decision.dropped_reason is None


def test_strict_call_contract_rejects_when_no_candidates() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=[],
        caller_module="app.mod",
        module_lookup={},
        import_targets={},
    )
    assert decision.accepted_candidate is None
    assert decision.accepted_provenance is None
    assert decision.dropped_reason == "no_candidates"
    assert decision.candidate_count == 0


def test_strict_call_contract_rejects_ambiguous_multiple_in_scope_candidates() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=["deps.a.S.run", "deps.b.S.run", "offscope.S.run"],
        caller_module="app.mod",
        module_lookup={
            "deps.a.S.run": "deps.a",
            "deps.b.S.run": "deps.b",
            "offscope.S.run": "offscope",
        },
        import_targets={"app.mod": {"deps.a", "deps.b"}},
    )
    assert decision.accepted_candidate is None
    assert decision.accepted_provenance is None
    assert decision.dropped_reason == "ambiguous_multiple_in_scope_candidates"


def test_strict_call_contract_rejects_ambiguous_without_in_scope_candidates() -> None:
    decision = select_strict_call_candidate(
        identifier="run",
        direct_candidates=[],
        fallback_candidates=["x.mod.S.run", "y.mod.S.run"],
        caller_module="app.mod",
        module_lookup={"x.mod.S.run": "x.mod", "y.mod.S.run": "y.mod"},
        import_targets={"app.mod": {"deps.a"}},
    )
    assert decision.accepted_candidate is None
    assert decision.accepted_provenance is None
    assert decision.dropped_reason == "ambiguous_no_in_scope_candidate"
