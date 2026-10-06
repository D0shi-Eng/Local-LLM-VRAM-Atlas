"""تحقق حي منفصل: عينة البذور الحقيقية فقط عند طلبها صراحة.

التشغيل الافتراضي يتجاوز هذه الاختبارات للحفاظ على عدم الاتصال.
التشغيل الحي: ATLAS_LIVE=1 python -m pytest tests/intake/test_live_seed.py -q
"""

import os

import pytest

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.pipeline import IntakePipeline

SEED_REPOS = [
    "openbmb/MiniCPM5-2B",
    "IFM/K2-Horizon-7B-GGUF",
    "Qwen/Qwen3.8-27B",
    "google/gemma-4-12B",
    "openai/gpt-oss-20b",
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
]

pytestmark = pytest.mark.live


def _live_client():
    """عميل حي بمهلة محدودة للتحقق اليدوي فقط."""
    return HuggingFaceSourceClient(timeout=20.0)


@pytest.mark.parametrize("repo_id", SEED_REPOS)
def test_live_seed_metadata_retrievable(repo_id):
    """كل بذرة حية تسترجع بياناتها الوصفية العامة دون اعتماد."""
    if os.environ.get("ATLAS_LIVE") != "1":
        pytest.skip("live verification requires ATLAS_LIVE=1")
    outcome = IntakePipeline(_live_client()).build(repo_id)
    assert outcome.model_record["display_name"] == repo_id
    assert outcome.intake_state in (
        "metadata_verified",
        "pending_license",
        "pending_metadata",
        "blocked",
    )
