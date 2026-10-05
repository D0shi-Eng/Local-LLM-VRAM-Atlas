"""اختبارات CLI للمرحلة الثانية: الأوامر ورموز الخروج وJSON."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = str(REPO_ROOT / "src")


def _run(*argv: str):
    """تشغيل CLI داخل المسار المعتمد ببيئة نظيفة."""
    env = {"PYTHONPATH": SRC, "PATH": os.environ.get("PATH", "")}
    proc = subprocess.run(
        [sys.executable, "-m", "atlas.cli.main", *argv],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=60,
    )
    return proc


def test_quantization_list_json():
    """atlas quantization list تعرض السجل النسخي بصيغة آلية."""
    proc = _run("quantization", "list", "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["registry_version"] == "0.2.0"
    assert payload["count"] > 10


def test_artifact_inspect_variants():
    """atlas artifact inspect يفصل المتغيرات ويكشف الشظايا."""
    proc = _run(
        "artifact",
        "inspect",
        "--model-id",
        "demo",
        "--file",
        "model-Q4_K_M.gguf:4000000000",
        "--file",
        "model-Q5_K_M.gguf:5000000000",
    )
    assert proc.returncode == 0, proc.stderr
    assert "artifact_set_count: 2" in proc.stdout


def test_memory_estimate_insufficient_evidence_exit_3():
    """غياب الأدلة يُعيد exit 3 لا رقمًا مخترعًا."""
    proc = _run("memory", "estimate", "--architecture-family", "standard_transformer")
    assert proc.returncode == 3, proc.stdout
    assert "insufficient_evidence" in proc.stdout


def test_memory_estimate_unsupported_exit_4():
    """البنية غير المدعومة تُعيد exit 4."""
    proc = _run(
        "memory",
        "estimate",
        "--architecture-family",
        "mla",
        "--layers",
        "32",
        "--kv-heads",
        "8",
        "--head-dim",
        "128",
        "--weight-bytes",
        "4000000000",
    )
    assert proc.returncode == 4, proc.stdout


def test_vram_classify_json():
    """atlas vram classify تُخرج قرارات الفئات الأربع."""
    proc = _run(
        "vram",
        "classify",
        "--lower-bytes",
        "4000000000",
        "--upper-bytes",
        "5000000000",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert len(payload["decisions"]) == 4
    assert payload["recommendation_headroom_status"] == "not_calibrated"


def test_vram_classify_insufficient_exit_3():
    """النطاق الناقص يُعيد exit 3."""
    proc = _run("vram", "classify", "--lower-bytes", "13000000000")
    assert proc.returncode == 3, proc.stdout
