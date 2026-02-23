#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _score(tp: int, fp: int, fn: int, fp_w: float, fn_w: float) -> float:
    den = tp + fp_w * fp + fn_w * fn
    if den <= 0:
        return 0.0
    return tp / den


def _corr(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n == 0 or n != len(ys):
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = sum((x - mx) ** 2 for x in xs) ** 0.5
    deny = sum((y - my) ** 2 for y in ys) ** 0.5
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline calibration helper for prompt reliability heuristic weights."
    )
    parser.add_argument("--labels-jsonl", type=Path, required=True)
    parser.add_argument(
        "--target-key",
        default="task_success",
        help="Binary or continuous ground-truth target field in JSONL.",
    )
    args = parser.parse_args()

    rows = []
    for line in args.labels_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))

    targets = [float(row.get(args.target_key, 0.0)) for row in rows]
    best = None
    for fp_w in (0.8, 1.0, 1.2, 1.5):
        for fn_w in (0.8, 1.0, 1.2, 1.5, 2.0):
            preds = [
                _score(
                    int(row.get("tp", 0)),
                    int(row.get("fp", 0)),
                    int(row.get("fn", 0)),
                    fp_w=fp_w,
                    fn_w=fn_w,
                )
                for row in rows
            ]
            score = _corr(preds, targets)
            candidate = {"fp_weight": fp_w, "fn_weight": fn_w, "corr": score}
            if best is None or candidate["corr"] > best["corr"]:
                best = candidate

    print(json.dumps({"best": best, "rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
