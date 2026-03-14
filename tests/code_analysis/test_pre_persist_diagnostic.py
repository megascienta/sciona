# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.code_analysis.diagnostics.pre_persist.classifier import (
    classify_no_in_repo_candidate,
)
from sciona.code_analysis.diagnostics.pre_persist.models import (
    DiagnosticMissObservation,
)


def test_classifier_marks_common_builtin_name() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="print",
        ordinal=1,
        callee_kind="terminal",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_standard_library_or_builtin"


def test_classifier_marks_dynamic_receiver_pattern() -> None:
    observation = DiagnosticMissObservation(
        language="python",
        file_path="pkg/main.py",
        caller_structural_id="caller",
        caller_qualified_name="repo.pkg.main.run",
        caller_module="repo.pkg.main",
        identifier="self.helper",
        ordinal=1,
        callee_kind="qualified",
    )

    classified = classify_no_in_repo_candidate(observation)

    assert classified.bucket == "likely_dynamic_dispatch_or_indirect"
