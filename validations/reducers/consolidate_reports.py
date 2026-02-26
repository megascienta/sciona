#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_markdown(report_dir: Path) -> str:
    rows: list[tuple[str, dict]] = []
    for path in sorted(report_dir.glob("*_reducer_validation.json")):
        repo = path.stem.replace("_reducer_validation", "")
        rows.append((repo, _load(path)))

    lines: list[str] = []
    lines.append("# Consolidated Reducer Validation Report")
    lines.append("")
    lines.append("## Verdict Matrix")
    lines.append("")
    lines.append("| Repo | Hard Passed | Strict P | Strict R | Overreach | Enriched R |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for repo, payload in rows:
        verdict = payload.get("run_verdict") or {}
        invariants = payload.get("invariants") or {}
        strict = payload.get("static_contract_alignment") or {}
        enriched = payload.get("enriched_truth_alignment") or {}
        hard_passed = verdict.get("hard_passed", invariants.get("hard_passed"))
        lines.append(
            "| "
            + " | ".join(
                [
                    repo,
                    _fmt(hard_passed),
                    _fmt(strict.get("static_contract_precision")),
                    _fmt(strict.get("static_contract_recall")),
                    _fmt(strict.get("static_overreach_rate")),
                    _fmt(enriched.get("reducer_vs_enriched_truth_recall")),
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Hard Failures")
    lines.append("")
    any_failures = False
    for repo, payload in rows:
        failures = ((payload.get("invariants") or {}).get("hard_failures") or [])
        if not failures:
            continue
        any_failures = True
        lines.append(f"### {repo}")
        for item in failures:
            lines.append(f"- {item}")
        lines.append("")
    if not any_failures:
        lines.append("- none")
        lines.append("")

    lines.append("## Priority Actions")
    lines.append("")
    for repo, payload in rows:
        board = payload.get("action_priority_board") or []
        lines.append(f"### {repo}")
        if not board:
            lines.append("- none")
            lines.append("")
            continue
        for item in board[:5]:
            lines.append(
                f"- [{item.get('priority')}] {item.get('area')}::{item.get('issue')} evidence={item.get('evidence')}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    root = Path(__file__).resolve().parent
    report_dir = root / "reports"
    output_path = report_dir / "consolidated_validation_report.md"
    content = build_markdown(report_dir)
    output_path.write_text(content, encoding="utf-8")
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
