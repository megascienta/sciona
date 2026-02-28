#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import argparse
import json
from statistics import mean, pstdev
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from validations.reducers.validation import config
from validations.reducers.validation.orchestrator import run_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SCIONA reducers against independent parsers.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--nodes", type=int, default=config.DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    parser.add_argument(
        "--seed-list",
        type=str,
        default="",
        help="Comma-separated seed list for repeated runs with summary stats.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root
    if not args.seed_list.strip():
        return run_validation(
            repo_root=repo_root,
            nodes=args.nodes,
            seed=args.seed,
        )
    seeds = [int(item.strip()) for item in args.seed_list.split(",") if item.strip()]
    if not seeds:
        raise SystemExit("--seed-list provided but no valid seeds were parsed")
    runs: list[dict] = []
    for seed in seeds:
        rc = run_validation(
            repo_root=repo_root,
            nodes=args.nodes,
            seed=seed,
        )
        if rc != 0:
            return rc
        report_path = config.report_paths(repo_root.resolve()).json_path
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        q2 = (payload.get("questions") or {}).get("q2") or {}
        runs.append(
            {
                "seed": seed,
                "avg_missing_rate": q2.get("avg_missing_rate"),
                "avg_spillover_rate": q2.get("avg_spillover_rate"),
                "avg_mutual_accuracy": q2.get("avg_mutual_accuracy"),
            }
        )
    def _series(key: str) -> list[float]:
        return [float(run[key]) for run in runs if run.get(key) is not None]
    for metric in ("avg_missing_rate", "avg_spillover_rate", "avg_mutual_accuracy"):
        values = _series(metric)
        if not values:
            print(f"{metric}: n=0")
            continue
        std = pstdev(values) if len(values) > 1 else 0.0
        print(f"{metric}: n={len(values)} mean={mean(values):.6f} stddev={std:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
