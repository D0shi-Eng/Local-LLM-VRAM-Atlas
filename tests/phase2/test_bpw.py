"""اختبارات البت الفعال والدقة المختلطة."""

from atlas.quant.bpw import effective_bits_per_weight, weight_bytes_from_bpw
from atlas.quant.detection import detect_from_tensor_inventory
from atlas.quant.registry import find_entry


def test_effective_bpw_hand_calculated():
    """الحساب اليدوي: (bytes*8)/params دون تخمين."""
    assert effective_bits_per_weight(1_000_000_000, 2_000_000_000) == 4.0


def test_effective_bpw_refuses_missing_inputs():
    """غياب أي مدخل يعني unknown لا صفرًا."""
    assert effective_bits_per_weight(None, 2_000_000_000) is None
    assert effective_bits_per_weight(1_000_000_000, None) is None
    assert effective_bits_per_weight(0, 100) is None
    assert effective_bits_per_weight(100, 0) is None


def test_weight_bytes_from_documented_bpw():
    """اشتقاق البايت من bpw موثق فقط."""
    assert weight_bytes_from_bpw(2_000_000_000, 4.0) == 1_000_000_000
    assert weight_bytes_from_bpw(None, 4.0) is None
    assert weight_bytes_from_bpw(2_000_000_000, None) is None


def test_q4_name_is_not_4_bpw():
    """اسم Q4_K_M المختلط لا يحمل bpw مفردًا؛ Q8_0 ليست 8.0 بت."""
    mixed = find_entry("Q4_K_M")
    assert mixed is not None
    assert mixed["nominal_bits"] == 4.0
    assert mixed["effective_bits_per_weight"] is None
    assert mixed["mixed_precision"] is True
    plain = find_entry("Q8_0")
    assert plain is not None
    assert plain["effective_bits_per_weight"] == 8.5


def test_mixed_precision_detected_from_distribution():
    """توزيع الأنواع المختلط يُسجل دون اختزال لبت واحد."""
    mixed = detect_from_tensor_inventory(
        [{"precision": "Q4_K_M"}] * 100 + [{"precision": "Q6_K"}] * 28
    )
    assert mixed["mixed_precision"] is True
    assert mixed["detection_method"] == "verified_metadata"
    single = detect_from_tensor_inventory([{"precision": "Q4_K_M"}] * 128)
    assert single["mixed_precision"] is False
