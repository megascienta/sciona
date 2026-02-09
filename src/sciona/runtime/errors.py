# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Cross-layer SCIONA error hierarchy."""

from __future__ import annotations

from dataclasses import dataclass

from .rollback import RollbackPolicy


@dataclass
class ScionaError(RuntimeError):
    """Base error carrying structured metadata for CLI handling."""

    message: str
    code: str = "error"
    exit_code: int | None = None
    hint: str | None = None
    severity: str | None = None
    origin_layer: str | None = None
    status_code: int | None = None
    rollback_policy: RollbackPolicy | None = None

    DEFAULT_EXIT_CODE = 1
    DEFAULT_SEVERITY = "error"
    DEFAULT_ORIGIN_LAYER = "runtime"
    DEFAULT_STATUS_CODE = 400
    DEFAULT_ROLLBACK_POLICY = RollbackPolicy.CORE_ONLY

    def __post_init__(self) -> None:
        if self.exit_code is None:
            self.exit_code = getattr(self, "DEFAULT_EXIT_CODE", 1)
        if self.severity is None:
            self.severity = getattr(self, "DEFAULT_SEVERITY", "error")
        if self.origin_layer is None:
            self.origin_layer = getattr(self, "DEFAULT_ORIGIN_LAYER", "runtime")
        if self.status_code is None:
            self.status_code = getattr(self, "DEFAULT_STATUS_CODE", 400)
        if self.rollback_policy is None:
            self.rollback_policy = getattr(
                self, "DEFAULT_ROLLBACK_POLICY", RollbackPolicy.CORE_ONLY
            )

    def __str__(self) -> str:
        return self.message


class ConfigError(ScionaError):
    DEFAULT_ORIGIN_LAYER = "config"


class EnvError(ScionaError):
    DEFAULT_ORIGIN_LAYER = "env"


class SetupError(ScionaError):
    DEFAULT_ORIGIN_LAYER = "setup"
    DEFAULT_ROLLBACK_POLICY = RollbackPolicy.NONE


class WorkflowError(ScionaError):
    DEFAULT_ORIGIN_LAYER = "workflow"
    DEFAULT_ROLLBACK_POLICY = RollbackPolicy.PAIR_REQUIRED


class GitError(EnvError):
    DEFAULT_ORIGIN_LAYER = "git"
    DEFAULT_ROLLBACK_POLICY = RollbackPolicy.NONE


class IngestionError(ScionaError):
    DEFAULT_ORIGIN_LAYER = "code_analysis"


class NotInitializedError(SetupError):
    DEFAULT_EXIT_CODE = 2
    hint = "Run `sciona init` in the repository root."


class CorruptVersionFileError(SetupError):
    DEFAULT_EXIT_CODE = 3
    hint = "Remove `.sciona/version.json` and re-run `sciona init`."


class SchemaMismatchError(SetupError):
    DEFAULT_EXIT_CODE = 4
    hint = "Remove `.sciona` and re-run `sciona init` to rebuild the database."


class VersionMismatchError(SetupError):
    DEFAULT_EXIT_CODE = 5
    hint = "Update SCIONA or reinitialize the repository."


__all__ = [
    "ScionaError",
    "ConfigError",
    "EnvError",
    "SetupError",
    "WorkflowError",
    "GitError",
    "IngestionError",
    "NotInitializedError",
    "CorruptVersionFileError",
    "SchemaMismatchError",
    "VersionMismatchError",
]
