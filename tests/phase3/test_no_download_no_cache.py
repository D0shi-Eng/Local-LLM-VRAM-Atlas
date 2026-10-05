"""Phase 3: zero-weight regression — no downloader/loader is ever referenced."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = [REPO_ROOT / "src" / "atlas" / "archinfo", REPO_ROOT / "src" / "atlas" / "memory"]

FORBIDDEN_CALLS = (
    "hf_hub_download",
    "snapshot_download",
    "from_pretrained",
    "AutoModel",
    "AutoTokenizer",
    "llama_cpp",
    "ExLlamaV2",
    "snapshot_download",
)

FORBIDDEN_CACHE_MARKERS = (
    ".cache/huggingface",
    "huggingface/hub",
    "HF_HOME",
    "HUGGINGFACE_HUB_CACHE",
)


def _iter_python_files():
    for root in SCAN_ROOTS:
        yield from root.rglob("*.py")


def test_no_weight_download_or_loader_references():
    """AST + text scan: arch/memory subsystems never call weight loaders."""
    violations: list[str] = []
    for path in _iter_python_files():
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for marker in FORBIDDEN_CALLS:
            if marker in names or marker in text:
                violations.append(f"{path.name}: {marker}")
    assert violations == [], f"weight loader references found: {violations}"


def test_no_model_cache_side_effect_markers():
    """No cache-directory creation markers in Phase 3 architecture/memory code."""
    violations = []
    for path in _iter_python_files():
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_CACHE_MARKERS:
            if marker in text:
                violations.append(f"{path.name}: {marker}")
    assert violations == []


def test_no_trust_remote_code_execution():
    """Remote-code execution is absent from the new subsystems.

    The Phase 2 contract forbids even the literal token in src: custom code
    is detected via the ``auto_map`` key and reported as
    ``custom_remote_architecture`` without ever executing it.
    """
    violations = []
    for path in _iter_python_files():
        text = path.read_text(encoding="utf-8")
        for marker in (
            "trust_remote_code",
            "exec(",
            "eval(",
            "__import__",
            "importlib.import_module",
        ):
            if marker in text:
                violations.append(f"{path.name}: {marker}")
    assert violations == []


def test_runtime_and_measurement_modules_clean(tmp_path, monkeypatch):
    """Importing runtimes/measurements creates no cache and downloads nothing."""
    monkeypatch.chdir(tmp_path)
    from atlas.measurements.registry import ExternalMeasurement, validate_measurement
    from atlas.runtimes.knowledge import list_capabilities

    assert len(list_capabilities()) >= 5
    measurement = ExternalMeasurement(
        measurement_id="ex-1",
        model_id="org/model",
        evidence_level="community_measurement",
    )
    assert validate_measurement(measurement) == []
    assert list(tmp_path.iterdir()) == []
