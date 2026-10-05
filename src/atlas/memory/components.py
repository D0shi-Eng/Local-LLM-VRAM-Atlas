"""مكونات الذاكرة: تمثيل VRAM كأجزاء مسماة لا رقم مفرد."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MemoryComponents:
    """مكونات ذاكرة الجهاز؛ المجهول يبقى None ولا يتحول إلى صفر."""

    device_weight_bytes: int | None = None
    kv_or_state_cache_bytes: int | None = None
    runtime_static_bytes: int | None = None
    runtime_dynamic_bytes: int | None = None
    compute_workspace_bytes: int | None = None
    graph_buffer_bytes: int | None = None
    output_buffer_bytes: int | None = None
    multimodal_component_bytes: int | None = None
    speculative_decoding_bytes: int | None = None
    other_known_bytes: int | None = None
    unknown_overhead: tuple[str, ...] = field(default_factory=tuple)

    def known_total_bytes(self) -> int:
        """مجموع المكونات المعلومة فقط دون افتراض عن المجهول."""
        total = 0
        for value in (
            self.device_weight_bytes,
            self.kv_or_state_cache_bytes,
            self.runtime_static_bytes,
            self.runtime_dynamic_bytes,
            self.compute_workspace_bytes,
            self.graph_buffer_bytes,
            self.output_buffer_bytes,
            self.multimodal_component_bytes,
            self.speculative_decoding_bytes,
            self.other_known_bytes,
        ):
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                total += value
        return total

    def unknown_components(self) -> tuple[str, ...]:
        """أسماء المكونات المجهولة التي تمنع الحد العلوي الموثوق."""
        missing: list[str] = []
        for name in (
            "device_weight_bytes",
            "kv_or_state_cache_bytes",
            "runtime_static_bytes",
            "runtime_dynamic_bytes",
            "compute_workspace_bytes",
            "graph_buffer_bytes",
            "output_buffer_bytes",
            "multimodal_component_bytes",
            "speculative_decoding_bytes",
            "other_known_bytes",
        ):
            if getattr(self, name) is None:
                missing.append(name)
        missing.extend(item for item in self.unknown_overhead if item not in missing)
        return tuple(missing)
