# SPDX-License-Identifier: MIT

from __future__ import annotations

from datetime import date

from validations.reducers.validation import config


def test_repo_kind_precision_overrides_loaded_from_calibration_file() -> None:
    assert config.REPO_KIND_PRECISION_OVERRIDES.get("fastapi", {}).get("method") == 0.25
    assert config.REPO_KIND_PRECISION_OVERRIDES.get("nest", {}).get("function") == 0.35


def test_stale_repo_override_warnings_detects_expired_rows() -> None:
    warnings = config.stale_repo_override_warnings(
        today=date(2026, 2, 26),
        metadata=[
            {
                "repo": "demo",
                "kind": "function",
                "min_precision": 0.1,
                "expires_on": "2026-02-01",
            },
            {
                "repo": "demo",
                "kind": "method",
                "min_precision": 0.1,
                "expires_on": "2026-03-01",
            },
        ],
    )
    assert len(warnings) == 1
    assert "demo::function" in warnings[0]
