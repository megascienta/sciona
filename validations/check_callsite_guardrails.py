#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sciona.pipelines.exec.guardrails import evaluate_non_test_callsite_guardrails


def _parse_threshold(value: str) -> tuple[str, float]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("threshold must use language=value format")
    language, raw = value.split("=", 1)
    language = language.strip().lower()
    if not language:
        raise argparse.ArgumentTypeError("threshold language cannot be empty")
    try:
        threshold = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("threshold must be a float") from exc
    if threshold < 0.0 or threshold > 1.0:
        raise argparse.ArgumentTypeError("threshold must be between 0 and 1")
    return language, threshold


def _load_thresholds(
    *,
    config_path: Path | None,
    overrides: list[tuple[str, float]],
) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    if config_path is not None:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        configured = payload.get("non_tests_min_success_rate", {})
        if not isinstance(configured, dict):
            raise ValueError("config.non_tests_min_success_rate must be an object")
        for language, threshold in configured.items():
            thresholds[str(language).strip().lower()] = float(threshold)
    for language, threshold in overrides:
        thresholds[language] = threshold
    return thresholds


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate per-language non-test callsite acceptance guardrails "
            "from a sciona status --json payload."
        )
    )
    parser.add_argument(
        "--status-json",
        required=True,
        help="Path to status JSON payload.",
    )
    parser.add_argument(
        "--config",
        default="validations/callsite_guardrails.json",
        help="Path to guardrail config JSON.",
    )
    parser.add_argument(
        "--threshold",
        action="append",
        default=[],
        type=_parse_threshold,
        help="Override threshold using language=value (for example: python=0.90).",
    )
    args = parser.parse_args()

    status_path = Path(args.status_json)
    config_path = Path(args.config) if args.config else None
    if config_path is not None and not config_path.exists():
        config_path = None

    thresholds = _load_thresholds(
        config_path=config_path,
        overrides=list(args.threshold),
    )
    if not thresholds:
        raise SystemExit("No thresholds configured. Add --threshold or a config file.")

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    results = evaluate_non_test_callsite_guardrails(
        payload,
        min_success_rate_by_language=thresholds,
    )
    failures = [item for item in results if not item.passed]
    for item in results:
        if item.skipped_reason:
            print(
                f"[SKIP] {item.language}: {item.skipped_reason} "
                f"(threshold={item.threshold:.3f})"
            )
            continue
        print(
            f"[{'PASS' if item.passed else 'FAIL'}] {item.language}: "
            f"non_tests success={item.success_rate:.3f} "
            f"(eligible={item.eligible}, threshold={item.threshold:.3f})"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
