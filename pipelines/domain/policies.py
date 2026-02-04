"""Policy objects that decouple orchestration from execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ...runtime.config import LanguageSettings


@dataclass(frozen=True)
class AnalysisPolicy:
    languages: Mapping[str, LanguageSettings]


@dataclass(frozen=True)
class ArtifactPolicy:
    refresh_artifacts: bool = True
    refresh_calls: bool = True


@dataclass(frozen=True)
class BuildPolicy:
    analysis: AnalysisPolicy
    artifacts: ArtifactPolicy


__all__ = ["AnalysisPolicy", "ArtifactPolicy", "BuildPolicy"]
