# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Guardrail checks for status-report callsite metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    language: str
    eligible: int
    success_rate: float | None
    threshold: float
    passed: bool
    skipped_reason: str | None = None


def evaluate_non_test_callsite_guardrails(
    report_payload: dict[str, object],
    *,
    min_success_rate_by_language: dict[str, float],
) -> list[GuardrailResult]:
    report = report_payload.get("report")
    if not isinstance(report, dict):
        raise ValueError("status payload missing report")
    languages = report.get("languages")
    if not isinstance(languages, dict):
        raise ValueError("status payload missing report.languages")

    results: list[GuardrailResult] = []
    for language, item in languages.items():
        if not isinstance(item, dict):
            continue
        language = str(language or "").strip()
        if not language:
            continue
        if language not in min_success_rate_by_language:
            continue
        threshold = float(min_success_rate_by_language[language])
        scope = item.get("scopes")
        if not isinstance(scope, dict):
            results.append(
                GuardrailResult(
                    language=language,
                    eligible=0,
                    success_rate=None,
                    threshold=threshold,
                    passed=True,
                    skipped_reason="scopes_unavailable",
                )
            )
            continue
        non_tests = scope.get("non_tests")
        if not isinstance(non_tests, dict):
            results.append(
                GuardrailResult(
                    language=language,
                    eligible=0,
                    success_rate=None,
                    threshold=threshold,
                    passed=True,
                    skipped_reason="non_tests_funnel_unavailable",
                )
            )
            continue
        eligible = int(non_tests.get("persisted_callsites") or 0)
        accepted = non_tests.get("persisted_accepted")
        success_rate = None
        if accepted is not None and eligible > 0:
            success_rate = float(accepted) / float(eligible)
        if eligible <= 0 or success_rate is None:
            results.append(
                GuardrailResult(
                    language=language,
                    eligible=eligible,
                    success_rate=success_rate,
                    threshold=threshold,
                    passed=True,
                    skipped_reason="no_non_test_persisted_callsites",
                )
            )
            continue
        passed = success_rate >= threshold
        results.append(
            GuardrailResult(
                language=language,
                eligible=eligible,
                success_rate=success_rate,
                threshold=threshold,
                passed=passed,
            )
        )
    return results


__all__ = ["GuardrailResult", "evaluate_non_test_callsite_guardrails"]
