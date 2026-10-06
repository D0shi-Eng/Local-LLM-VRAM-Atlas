"""جلب البيانات الوصفية: allowlist صارمة دون تنفيذ شيفرة."""

from __future__ import annotations

import json
import urllib.request

from atlas.intake.errors import IntakeError, SourceUnavailableError
from atlas.intake.url_safety import assert_safe_url, is_safe_url

# أنواع البيانات الوصفية الصغيرة المسموحة فقط (لا أوزان أبدًا).
ALLOWED_SUFFIXES = (
    "config.json",
    "quantization_config.json",
    "model.safetensors.index.json",
    ".index.json",
)

# مضيفو المصادر المسموحين (مستودع عام واحد فقط).
ALLOWED_HOSTS = ("huggingface.co", "cdn-lfs.huggingface.co")

# حدود صارمة: حجم ومهلة وميزانية تراكمية.
MAX_METADATA_BYTES = 256 * 1024
DEFAULT_TIMEOUT = 10.0
MAX_REQUESTS_PER_RUN = 12


class MetadataBudget:
    """ميزانية تراكمية لطلبات البيانات الوصفية."""

    def __init__(self, limit: int = MAX_REQUESTS_PER_RUN) -> None:
        """تهيئة الميزانية بالحد الأقصى للطلبات."""
        self._limit = limit
        self._used = 0

    @property
    def used(self) -> int:
        """عدد الطلبات المستهلكة."""
        return self._used

    def consume(self) -> None:
        """استهلاك طلب واحد أو الرفض عند نفاد الميزانية."""
        if self._used >= self._limit:
            raise SourceUnavailableError(
                "metadata request budget exhausted: refusing further fetches"
            )
        self._used += 1


def allowed_metadata_url(url: str) -> bool:
    """فحص العنوان ضد allowlist الامتداد والمضيف."""
    if not is_safe_url(url):
        return False
    try:
        from urllib.parse import urlparse as _parse

        host = (_parse(url).hostname or "").lower()
    except ValueError:
        return False
    if host not in ALLOWED_HOSTS:
        return False
    lowered = url.split("?", 1)[0].lower()
    return any(lowered.endswith(suffix) for suffix in ALLOWED_SUFFIXES)


def fetch_small_json(
    url: str, *, timeout: float = DEFAULT_TIMEOUT, budget: MetadataBudget | None = None
) -> dict:
    """جلب JSON صغير من مصدر مسموح مع حدود صارمة."""
    assert_safe_url(url)
    if not allowed_metadata_url(url):
        raise SourceUnavailableError(f"metadata url not in allowlist: {url!r}")
    if budget is not None:
        budget.consume()
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": "atlas-metadata/0.2.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            ctype = (response.headers.get("Content-Type") or "").lower()
            if "json" not in ctype and "octet" not in ctype and "text" not in ctype:
                raise SourceUnavailableError(f"unexpected content-type for metadata: {ctype!r}")
            raw = response.read(MAX_METADATA_BYTES + 1)
    except IntakeError:
        raise
    except Exception as exc:  # noqa: BLE001 - تغليف مقصود لأخطاء الشبكة
        raise SourceUnavailableError(f"metadata fetch failed: {exc}") from exc
    if len(raw) > MAX_METADATA_BYTES:
        raise SourceUnavailableError("metadata exceeds strict size cap: refusing to parse")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SourceUnavailableError(f"metadata is not safe JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SourceUnavailableError("metadata JSON must be an object")
    return parsed
