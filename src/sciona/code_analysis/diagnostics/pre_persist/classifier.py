# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Best-effort classification for no-in-repo-candidate observations."""

from __future__ import annotations

from .languages import java, javascript, python, typescript
from .languages.common import classify_common
from .models import DiagnosticClassification, DiagnosticMissObservation


def classify_no_in_repo_candidate(
    observation: DiagnosticMissObservation,
) -> DiagnosticClassification:
    language = observation.language.strip().lower()
    if language == "python":
        classified = python.classify(observation)
    elif language == "javascript":
        classified = javascript.classify(observation)
    elif language == "typescript":
        classified = typescript.classify(observation)
    elif language == "java":
        classified = java.classify(observation)
    else:
        classified = None
    if classified is not None:
        return classified
    return classify_common(observation)
