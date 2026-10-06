"""اختبارات تجميع الartifacts: الشظايا والمتغيرات والمرافقات."""

from atlas.artifact.grouping import group_siblings
from atlas.validation.validator import validate_record


def _sibling(filename: str, size: int | None) -> dict:
    """بناء مدخل أخ من الاسم والحجم المبلغ عنه فقط."""
    lowered = filename.lower()
    extension = "." + lowered.rsplit(".", 1)[-1] if "." in lowered.rsplit("/", 1)[-1] else ""
    return {
        "filename": filename,
        "path": filename,
        "extension": extension,
        "source_reported_size_bytes": size,
    }


def _as_record(artifact_set, model_id: str = "demo-model") -> dict:
    """تحويل مجموعة إلى سجل JSON قابل للتحقق."""
    return {
        "schema_version": "0.2.0",
        "artifact_set_id": artifact_set.artifact_set_id,
        "model_id": artifact_set.model_id,
        "revision": artifact_set.revision,
        "variant": artifact_set.variant,
        "format": artifact_set.format,
        "kind": artifact_set.kind,
        "files": [
            {
                "filename": item.filename,
                "path": item.path,
                "extension": item.extension,
                "source_reported_size_bytes": item.source_reported_size_bytes,
            }
            for item in artifact_set.files
        ],
        "shard_count": artifact_set.shard_count,
        "shard_total": artifact_set.shard_total,
        "shards_complete": artifact_set.shards_complete,
        "total_source_reported_bytes": artifact_set.total_source_reported_bytes,
        "primary_weight_bytes": artifact_set.primary_weight_bytes,
        "auxiliary_bytes": artifact_set.auxiliary_bytes,
        "companion_components": list(artifact_set.companion_components),
        "verification_status": artifact_set.verification_status,
    }


def test_shard_grouping_and_total():
    """شظايا نفس الجذع تُجمع ويُحسب مجموعها."""
    sets, _aux, _warnings = group_siblings(
        [
            _sibling("model-00001-of-00003.gguf", 1_000_000_000),
            _sibling("model-00002-of-00003.gguf", 1_000_000_000),
            _sibling("model-00003-of-00003.gguf", 1_000_000_000),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert len(sets) == 1
    assert sets[0].kind == "sharded"
    assert sets[0].shards_complete is True
    assert sets[0].total_source_reported_bytes == 3_000_000_000
    assert validate_record(_as_record(sets[0]), "artifact") == []


def test_missing_shard_detected():
    """الشظية المفقودة تُكتشف ولا تُخفى."""
    _sets, _aux, warnings = group_siblings(
        [
            _sibling("model-00001-of-00003.gguf", 1_000_000_000),
            _sibling("model-00003-of-00003.gguf", 1_000_000_000),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert any("missing_shard" in item for item in warnings)


def test_duplicate_shard_detected():
    """الشظية المكررة تُكتشف."""
    _sets, _aux, warnings = group_siblings(
        [
            _sibling("model-00001-of-00002.gguf", 5),
            _sibling("model-00001-of-00002.gguf", 5),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert any("duplicate_shard" in item for item in warnings)


def test_quant_variants_stay_separate():
    """متغيرات الكم المختلفة ليست شظايا ولا تُدمج."""
    sets, _aux, warnings = group_siblings(
        [
            _sibling("model-Q4_K_M.gguf", 4_000_000_000),
            _sibling("model-Q5_K_M.gguf", 5_000_000_000),
            _sibling("model-Q8_0.gguf", 8_000_000_000),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert len(sets) == 3
    assert any("multi_variant_repository" in item for item in warnings)


def test_bf16_variant_identified_separately():
    """متغير BF16 يُسجل منفصلًا عن الكمات."""
    sets, _aux, _warnings = group_siblings(
        [
            _sibling("model-BF16.gguf", 14_000_000_000),
            _sibling("model-Q4_K_M.gguf", 4_000_000_000),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert len(sets) == 2


def test_projector_is_companion_not_weight():
    """الprojector مكون مرافق لا جزء من حجم النموذج اللغوي."""
    sets, aux, _warnings = group_siblings(
        [
            _sibling("model-Q4_K_M.gguf", 4_000_000_000),
            _sibling("mmproj-model-f16.gguf", 500_000_000),
        ],
        model_id="demo-vlm",
        revision="abc123",
    )
    assert len(sets) == 1
    assert sets[0].primary_weight_bytes == 4_000_000_000
    assert "projector" in list(sets[0].companion_components) or any(
        "mmproj" in item.filename for item in aux
    )


def test_repository_total_never_used_as_model_size():
    """كل مجموعة تحمل مجموعها الخاص لا مجموع المستودع."""
    sets, _aux, _warnings = group_siblings(
        [
            _sibling("model-Q4_K_M.gguf", 4_000_000_000),
            _sibling("model-Q8_0.gguf", 8_000_000_000),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    totals = sorted(item.total_source_reported_bytes or 0 for item in sets)
    assert totals == [4_000_000_000, 8_000_000_000]
    assert sum(totals) != sets[0].total_source_reported_bytes


def test_imatrix_file_is_auxiliary_not_variant():
    """ملف imatrix مساعد لا متغير وزن منفصل."""
    sets, aux, _warnings = group_siblings(
        [
            _sibling("model-Q4_K_M.gguf", 4_000_000_000),
            _sibling("model-imatrix.gguf", 28_000_000),
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert len(sets) == 1
    assert sets[0].variant == "Q4_K_M"
    assert any("imatrix" in item.filename for item in aux)


def test_subdirectory_copies_stay_separate_sets():
    """نسخ الدلائل الفرعية (original/metal) مجموعات مستقلة."""
    sets, _aux, _warnings = group_siblings(
        [
            {
                "filename": "model-00001-of-00002.safetensors",
                "path": "x",
                "extension": ".safetensors",
                "source_reported_size_bytes": 5,
            },
            {
                "filename": "model-00002-of-00002.safetensors",
                "path": "x",
                "extension": ".safetensors",
                "source_reported_size_bytes": 5,
            },
            {
                "filename": "original/model.safetensors",
                "path": "x",
                "extension": ".safetensors",
                "source_reported_size_bytes": 9,
            },
        ],
        model_id="demo-model",
        revision="abc123",
    )
    assert len(sets) == 2
    sharded = [item for item in sets if item.kind == "sharded"]
    assert len(sharded) == 1
    assert sharded[0].shards_complete is True


def test_single_file_of_00001_is_complete():
    """ملف وحيد 00000-of-00001 مكتمل لا مفقود."""
    sets, _aux, warnings = group_siblings(
        [_sibling("model-00000-of-00001.safetensors", 5_000_000_000)],
        model_id="demo-model",
        revision="abc123",
    )
    assert len(sets) == 1
    assert sets[0].kind == "sharded"
    assert sets[0].shards_complete is True
    assert not any("missing_shard" in item for item in warnings)
