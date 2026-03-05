# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helpers for onboarding new language adapters."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.extract.contracts.language_adapter import LanguageDescriptor


@dataclass(frozen=True)
class OnboardingValidationResult:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def validate_language_onboarding(
    descriptor: LanguageDescriptor,
    *,
    capability_keys: set[str],
    declared_parity_dimensions: set[str],
    required_parity_dimensions: set[str],
) -> OnboardingValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not descriptor.language_id:
        errors.append("language_id is required")
    if not descriptor.extensions:
        errors.append("extensions are required")
    if descriptor.extractor_factory is None:
        errors.append("extractor_factory is required")
    if descriptor.module_namer is None:
        errors.append("module_namer is required")
    if not descriptor.grammar_name:
        errors.append("grammar_name is required")
    if descriptor.query_set_version is None:
        errors.append("query_set_version is required")
    if not descriptor.callable_types:
        errors.append("callable_types are required")
    if not descriptor.capability_manifest_key:
        errors.append("capability_manifest_key is required")
    elif descriptor.capability_manifest_key not in capability_keys:
        errors.append(
            "capability_manifest_key "
            f"'{descriptor.capability_manifest_key}' missing from manifest keys"
        )

    missing_dims = sorted(required_parity_dimensions - declared_parity_dimensions)
    if missing_dims:
        errors.append(
            "missing parity dimensions: " + ", ".join(missing_dims)
        )

    extra_dims = sorted(declared_parity_dimensions - required_parity_dimensions)
    if extra_dims:
        warnings.append("extra parity dimensions: " + ", ".join(extra_dims))

    return OnboardingValidationResult(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


__all__ = ["OnboardingValidationResult", "validate_language_onboarding"]
