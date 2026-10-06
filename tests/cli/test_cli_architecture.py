"""CLI surface for arch, runtime and measurement commands (offline)."""

import json

from atlas.cli.main import main


def test_arch_resolve_from_config_file(tmp_path, capsys):
    config = {
        "model_type": "llama",
        "hidden_size": 4096,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    code = main(["arch", "resolve", "--config", str(path), "--revision", "abc123"])
    assert code == 0
    out = capsys.readouterr().out
    assert "architecture_family: llama" in out


def test_arch_resolve_insufficient_evidence_exit_3(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
    code = main(["arch", "resolve", "--config", str(path)])
    assert code == 3


def test_runtime_list_counts(capsys):
    assert main(["runtime", "list"]) == 0
    out = capsys.readouterr().out
    assert "count:" in out


def test_measurement_validate_roundtrip(tmp_path, capsys):
    record = {
        "schema_version": "0.3.0",
        "measurement_id": "m-010",
        "model_id": "org/model",
        "evidence_level": "community_measurement",
    }
    path = tmp_path / "measurement.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert main(["measurement", "validate", "--record", str(path)]) == 0
    out = capsys.readouterr().out
    assert "valid:" in out


def test_measurement_validate_rejects_bad_record(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"nope": True}), encoding="utf-8")
    assert main(["measurement", "validate", "--record", str(path)]) == 1
