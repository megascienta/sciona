# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from tests.code_analysis.parity_helpers import (
    assert_parity_expectations,
    build_snapshot,
    extension_for,
    language_specs,
)


def test_generated_parity_triplets(tmp_path: Path) -> None:
    root = Path("tests/fixtures/parity/generated")
    scenarios = sorted(
        path for path in root.iterdir() if path.is_dir() and (path / "expected.json").exists()
    )
    assert scenarios

    for scenario in scenarios:
        expected = json.loads((scenario / "expected.json").read_text(encoding="utf-8"))
        for rel_dir, fixture_name, analyzer, language in language_specs():
            source = (scenario / fixture_name).read_text(encoding="utf-8")
            ext = extension_for(language)
            rel_path = f"{scenario.name}/{rel_dir}/mod{ext}"
            path = tmp_path / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")

            snapshot = build_snapshot(path, rel_path, language, source)
            module_name = analyzer.module_name(tmp_path, snapshot)
            analyzer.module_index = {module_name}
            result = analyzer.analyze(snapshot, module_name)
            assert_parity_expectations(result, module_name, expected)
