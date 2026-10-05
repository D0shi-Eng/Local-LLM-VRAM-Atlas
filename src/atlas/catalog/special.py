"""Special-variant classification (Phase 4).

Evidence-backed only. Never labels post-training quants as native, never
merges ternary-native / post-training ternarization / TQ format, never
treats uncensored/abliterated/heretic as quality signals.
"""

from __future__ import annotations

HIGH_COMPRESSION_FAMILIES = {"q2", "iq2", "iq1", "q1", "tq"}
HIGH_COMPRESSION_TOKENS = (
    "Q2_K",
    "IQ2_",
    "IQ1_",
    "Q1_0",
    "TQ1",
    "TQ2",
    "Q3_K",
    "IQ3_",
)


def compression_evidence(record: dict) -> dict:
    """Return structured high-compression evidence for one record."""
    quant = record.get("quantization") or {}
    qfam = str(quant.get("quant_family") or "unknown").lower()
    qname = str(quant.get("quant_name") or "").upper()
    bpw = quant.get("bits_per_weight")
    native = quant.get("native_quantization")
    reasons: list[str] = []
    is_high = False
    if qfam in HIGH_COMPRESSION_FAMILIES:
        is_high = True
        reasons.append(f"quant_family={qfam}")
    if any(tok in qname for tok in HIGH_COMPRESSION_TOKENS):
        is_high = True
        reasons.append(f"quant_name={qname}")
    if isinstance(bpw, (int, float)) and bpw <= 3.0:
        is_high = True
        reasons.append(f"effective_bpw={bpw}")
    if native is True and qfam in ("ternary", "mxfp4", "nvfp4"):
        is_high = True
        reasons.append("native_low_bit_architecture")
    return {
        "is_high_compression": is_high,
        "evidence": "; ".join(reasons) if reasons else "insufficient structured evidence",
        "detection": "source_reported_or_filename_inferred",
    }


def native_low_bit_status(record: dict) -> dict:
    """Native low-bit requires training-architecture evidence, not 1-2bit quants."""
    quant = record.get("quantization") or {}
    native = quant.get("native_quantization")
    fmt = str(quant.get("format") or "unknown")
    qfam = str(quant.get("quant_family") or "unknown")
    arch = str(record.get("architecture") or "unknown").lower()
    # Explicit native markers in architecture or native_ternary/native_1bit formats.
    native_markers = ("bitnet", "ternary", "1-bit", "1bit", "native", "falcon3", "olmo")
    has_marker = any(m in arch for m in native_markers)
    if native is True and (fmt.startswith("native") or qfam in ("ternary",)):
        return {"is_native_low_bit": True, "evidence": "native_quantization=true + native format"}
    if has_marker and native is True:
        return {"is_native_low_bit": True, "evidence": f"architecture={arch} + native flag"}
    # BitNet architecture name is source-reported training-architecture evidence
    # for native 1.58-bit (ternary-weight) training, distinct from post-training
    # 1-2bit quants. Recorded as source-reported claim, not verified measurement.
    if "bitnet" in arch:
        return {
            "is_native_low_bit": True,
            "evidence": f"architecture={arch} source-reported native 1.58-bit training",
        }
    # Post-training 1-2bit quants are never native.
    return {"is_native_low_bit": False, "evidence": "no native-training evidence"}


def ternary_status(record: dict) -> dict:
    """Keep ternary-native / post-training ternarization / TQ format separate."""
    quant = record.get("quantization") or {}
    qfam = str(quant.get("quant_family") or "unknown").lower()
    qname = str(quant.get("quant_name") or "").upper()
    native = quant.get("native_quantization")
    if qfam == "ternary" and native is True:
        return {"kind": "ternary-native", "evidence": "native ternary training"}
    if qfam == "tq" or "TQ" in qname:
        return {"kind": "tq-format", "evidence": f"quant_name={qname}"}
    if qfam in ("q1", "iq1", "q2", "iq2") and native is False:
        return {"kind": "post-training-lowbit", "evidence": "post-training quant, not ternary"}
    return {"kind": "not-ternary", "evidence": "no ternary evidence"}


def alignment_claim(record: dict) -> dict:
    """Extract alignment-variant claim as author claim, never verification."""
    alignment = record.get("alignment") or {}
    variant = str(alignment.get("alignment_variant") or "unknown")
    claimed = alignment.get("uncensored_claimed")
    method = alignment.get("uncensoring_method")
    author = alignment.get("variant_author")
    base = alignment.get("base_model")
    verification = alignment.get("verification_status") or "unknown"
    return {
        "alignment_variant": variant,
        "claimed": bool(claimed) if claimed is not None else (variant != "unknown"),
        "variant_author": author,
        "base_model": base,
        "method": method or "publisher_or_variant_author_claim",
        "verification_status": verification,
        "note": "variant_author_claim unless stronger evidence exists; never a quality signal",
    }
