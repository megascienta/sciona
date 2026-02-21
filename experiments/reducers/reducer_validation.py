#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from experiments.reducers.validation import config
from experiments.reducers.validation.independent.shared import FileParseResult
from experiments.reducers.validation.orchestrator import run_validation
from experiments.reducers.validation.stability import independent_results_hash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SCIONA reducers against independent parsers.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--nodes", type=int, default=config.DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    parser.add_argument("--stability-runs", type=int, default=2)
    return parser.parse_args()


def _independent_results_hash(
    independent_results: Dict[str, FileParseResult],
    normalized_edge_map: Dict[str, Tuple[List[object], List[object]]],
) -> str:
    # Backward-compatibility shim for tests and external callers.
    return independent_results_hash(independent_results, normalized_edge_map)


def main() -> int:
    args = parse_args()
    return run_validation(
        repo_root=args.repo_root,
        nodes=args.nodes,
        seed=args.seed,
        stability_runs=args.stability_runs,
    )


if __name__ == "__main__":
    raise SystemExit(main())
