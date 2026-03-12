# SPDX-License-Identifier: MIT

from sciona.pipelines.exec.guardrails import evaluate_non_test_callsite_guardrails


def test_guardrails_pass_and_fail_by_language() -> None:
    payload = {
        "summary": {
            "languages": [
                {
                    "language": "python",
                    "call_site_funnel_by_scope": {
                        "non_tests": {
                            "persisted_callsites": 100,
                            "persisted_accepted": 92,
                        }
                    },
                },
                {
                    "language": "java",
                    "call_site_funnel_by_scope": {
                        "non_tests": {
                            "persisted_callsites": 100,
                            "persisted_accepted": 80,
                        }
                    },
                },
            ]
        }
    }
    results = evaluate_non_test_callsite_guardrails(
        payload,
        min_success_rate_by_language={"python": 0.9, "java": 0.9},
    )
    by_language = {item.language: item for item in results}
    assert by_language["python"].passed is True
    assert by_language["java"].passed is False


def test_guardrails_skip_when_non_test_scope_unavailable() -> None:
    payload = {
        "summary": {
            "languages": [
                {
                    "language": "typescript",
                    "call_site_funnel_by_scope": {
                        "non_tests": {
                            "persisted_callsites": 0,
                            "persisted_accepted": 0,
                        }
                    },
                }
            ]
        }
    }
    results = evaluate_non_test_callsite_guardrails(
        payload,
        min_success_rate_by_language={"typescript": 0.9},
    )
    assert len(results) == 1
    assert results[0].passed is True
    assert results[0].skipped_reason == "no_non_test_persisted_callsites"
