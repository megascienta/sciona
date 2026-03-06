# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Stable call-resolution stage contract shared across layers."""

from __future__ import annotations

STAGE_RECEIVER_TYPED = "receiver_typed_or_instance_mapped"
STAGE_ALIAS_NARROWING = "import_or_member_alias_narrowing"
STAGE_CLASSIFIER_SCOPED = "classifier_scoped_fallback"
STAGE_MODULE_SCOPED = "module_scoped_fallback"

REQUIRED_RESOLUTION_STAGES = (
    STAGE_RECEIVER_TYPED,
    STAGE_ALIAS_NARROWING,
    STAGE_CLASSIFIER_SCOPED,
    STAGE_MODULE_SCOPED,
)

STRICT_CANDIDATE_GATE_STAGE = "strict_candidate_gate"

__all__ = [
    "REQUIRED_RESOLUTION_STAGES",
    "STRICT_CANDIDATE_GATE_STAGE",
    "STAGE_ALIAS_NARROWING",
    "STAGE_CLASSIFIER_SCOPED",
    "STAGE_MODULE_SCOPED",
    "STAGE_RECEIVER_TYPED",
]
