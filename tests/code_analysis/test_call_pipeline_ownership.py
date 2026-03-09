# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from sciona.code_analysis.artifacts.rollups import _resolve_callees
from sciona.code_analysis.core.normalize.model import (
    AnalysisResult,
    CallRecord,
    EdgeRecord,
    FileRecord,
    FileSnapshot,
    SemanticNodeRecord,
)
from sciona.code_analysis.core.structural_assembler import StructuralAssembler


class _DummyConn:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("DB access is not expected in this test")


class _DummyStore:
    pass


def _snapshot() -> FileSnapshot:
    return FileSnapshot(
        record=FileRecord(
            path=Path("pkg/mod.py"),
            relative_path=Path("pkg/mod.py"),
            language="python",
        ),
        file_id="f1",
        blob_sha="hash",
        size=0,
        line_count=1,
        content=b"",
    )


def _module_node(qname: str) -> SemanticNodeRecord:
    return SemanticNodeRecord(
        language="python",
        node_type="module",
        qualified_name=qname,
        display_name=qname.rsplit(".", 1)[-1],
        file_path=Path("pkg/mod.py"),
        start_line=1,
        end_line=20,
    )


def _callable_node(qname: str) -> SemanticNodeRecord:
    return SemanticNodeRecord(
        language="python",
        node_type="callable",
        qualified_name=qname,
        display_name=qname.rsplit(".", 1)[-1],
        file_path=Path("pkg/mod.py"),
        start_line=1,
        end_line=5,
    )


def _core_observations(analysis: AnalysisResult) -> tuple[list[str], dict[str, object]]:
    assembler = StructuralAssembler(_DummyConn(), _DummyStore())
    observed = assembler._normalize_call_records(analysis, _snapshot())
    if not observed.call_records:
        return [], assembler.call_gate_diagnostics
    return list(observed.call_records[0].callee_identifiers), assembler.call_gate_diagnostics


def test_core_preserves_observed_callsites_while_artifacts_finalize_calls() -> None:
    analysis = AnalysisResult(
        nodes=[
            _module_node("pkg.alpha.task"),
            _module_node("pkg.alpha.util"),
            _module_node("pkg.beta.util"),
            _callable_node("pkg.alpha.task.entry"),
            _callable_node("pkg.alpha.util.helper"),
            _callable_node("pkg.beta.util.helper"),
        ],
        edges=[
            EdgeRecord(
                src_language="python",
                src_node_type="module",
                src_qualified_name="pkg.alpha.task",
                dst_language="python",
                dst_node_type="module",
                dst_qualified_name="pkg.alpha.util",
                edge_type="IMPORTS_DECLARED",
            )
        ],
        call_records=[
            CallRecord(
                qualified_name="pkg.alpha.task.entry",
                node_type="callable",
                callee_identifiers=["helper"],
            )
        ],
    )

    core_callees, core_diag = _core_observations(analysis)
    resolved_ids, _resolved_names, artifact_stats, callsite_rows = _resolve_callees(
        ("helper",),
        {"helper": ["alpha_helper", "beta_helper"]},
        caller_module="pkg.alpha.task",
        module_lookup={
            "alpha_helper": "pkg.alpha.util",
            "beta_helper": "pkg.beta.util",
        },
        callable_qname_by_id={
            "alpha_helper": "pkg.alpha.util.helper",
            "beta_helper": "pkg.beta.util.helper",
        },
        import_targets={"pkg.alpha.task": {"pkg.alpha.util"}},
        expanded_import_targets={"pkg.alpha.task": {"pkg.alpha.util"}},
        module_ancestors={"pkg.alpha.task": {"pkg.alpha"}},
    )

    assert core_callees == ["helper"]
    assert core_diag == {}
    assert resolved_ids == {"alpha_helper"}
    assert (artifact_stats.get("accepted_by_provenance") or {}).get("import_narrowed") == 1
    assert callsite_rows[0][3] == "import_narrowed"


def test_core_preserves_repo_wide_unresolved_observation_for_artifact_stage() -> None:
    analysis = AnalysisResult(
        nodes=[
            _module_node("pkg.mod"),
            _callable_node("pkg.mod.entry"),
        ],
        edges=[],
        call_records=[
            CallRecord(
                qualified_name="pkg.mod.entry",
                node_type="callable",
                callee_identifiers=["pkg.shared.helper"],
            )
        ],
    )

    core_callees, core_diag = _core_observations(analysis)
    resolved_ids, _resolved_names, artifact_stats, callsite_rows = _resolve_callees(
        ("pkg.shared.helper",),
        {"pkg.shared.helper": ["shared_helper"]},
        caller_module="pkg.mod",
        module_lookup={"shared_helper": "pkg.shared"},
        callable_qname_by_id={"shared_helper": "pkg.shared.helper"},
        import_targets={"pkg.mod": {"pkg.shared"}},
        expanded_import_targets={"pkg.mod": {"pkg.shared"}},
        module_ancestors={"pkg.mod": {"pkg"}},
    )

    assert core_callees == ["pkg.shared.helper"]
    assert core_diag == {}
    assert resolved_ids == {"shared_helper"}
    assert callsite_rows[0][3] == "exact_qname"
    assert (artifact_stats.get("accepted_by_provenance") or {}).get("exact_qname") == 1
