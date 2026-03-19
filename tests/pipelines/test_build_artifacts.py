# SPDX-License-Identifier: MIT

from __future__ import annotations

from sciona.pipelines.ops.build_artifacts import _stored_call_resolution_diagnostics


def test_stored_call_resolution_diagnostics_drops_bucket_and_observation_detail() -> None:
    payload = _stored_call_resolution_diagnostics(
        {
            "version": 1,
            "persisted_drop_observations": [{"identifier": "helper"}],
            "totals": {
                "observed_callsites": 3,
                "filtered_pre_persist_buckets": {"insufficient_static_evidence": 2},
                "persisted_callsite_pair_expansion": {
                    "persisted_callsites": 1,
                },
            },
            "by_caller": {
                "meth_alpha": {
                    "observed_callsites": 3,
                    "filtered_pre_persist_buckets": {
                        "insufficient_static_evidence": 2
                    },
                    "persisted_callsite_pair_expansion": {
                        "persisted_callsites": 1,
                    },
                }
            },
        }
    )

    assert "persisted_drop_observations" not in payload
    assert payload["totals"] == {"observed_callsites": 3}
    assert payload["by_caller"] == {
        "meth_alpha": {
            "observed_callsites": 3,
        }
    }
