# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "generator_spec.json"
OUTPUT_ROOT = ROOT / "generated"


LANGUAGE_EXT = {
    "python": "py",
    "typescript": "ts",
    "javascript": "js",
    "java": "java",
}


def main() -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios", [])
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for scenario in scenarios:
        _write_scenario(scenario)


def _write_scenario(scenario: dict[str, object]) -> None:
    name = str(scenario["name"])
    expected = scenario["expected"]
    sources = scenario["sources"]
    scenario_root = OUTPUT_ROOT / name
    scenario_root.mkdir(parents=True, exist_ok=True)
    (scenario_root / "expected.json").write_text(
        json.dumps(expected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for language, ext in LANGUAGE_EXT.items():
        source = str(sources[language])
        (scenario_root / f"{language}.{ext}").write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
