"""Live catalog validation (opt-in). Metadata-only, token=False, budgeted.

Run with: ATLAS_LIVE=1 python -m pytest tests/catalog/test_catalog_live.py -q
Default suite skips these.
"""

from __future__ import annotations

import os

import pytest

LIVE = os.environ.get("ATLAS_LIVE") == "1"

pytestmark = pytest.mark.live


@pytest.mark.skipif(not LIVE, reason="live metadata test (opt-in via ATLAS_LIVE=1)")
def test_live_seeds_metadata_only():
    from atlas.catalog.pipeline import fetch_candidates_live

    seeds = ["openbmb/MiniCPM5-2B", "Qwen/Qwen3-8B"]
    records, siblings, summary = fetch_candidates_live(seeds, timeout=15.0, budget_requests=5)
    assert summary.metadata_fetched >= 1
    for rec in records:
        assert rec.get("model_id")
        # No weight bytes downloaded: only source-reported sizes.
        quant = rec.get("quantization") or {}
        assert "file_size_bytes" in quant
