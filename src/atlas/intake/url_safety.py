"""حارس العناوين: منع الجلب التلقائي لأي مورد غير آمن."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

# عناوين خدمات البيانات الوصفية السحابية التي يجب حظرها صراحة.
_CLOUD_METADATA_IPS = {
    "169.254.169.254",
    "fd00:ec2::254",
}


def _parse_numeric_part(part: str) -> int | None:
    """تحليل جزء عددي واحد بقواعد الأساس الصريحة دون تخمين."""
    text = part.strip().lower()
    if not text:
        return None
    try:
        if text.startswith("0x") and len(text) > 2:
            return int(text, 16)
        if len(text) > 1 and text.startswith("0") and text.isdigit():
            return int(text, 8)
        if text.isdigit():
            return int(text, 10)
    except ValueError:
        return None
    return None


def _host_is_blocked_numeric(host: str) -> bool:
    """كشف عناوين IP المموهة عدديًا (عشرية/سداسية/ثمانية) وحظر الخاص منها."""
    parts = host.split(".")
    if len(parts) > 4:
        return False
    numbers: list[int] = []
    for part in parts:
        # الصيغة المفردة الكاملة مثل 2130706433 تعالج كعدد واحد.
        if len(parts) == 1 and part.lower().startswith("0x"):
            value = _parse_numeric_part(part)
        else:
            value = _parse_numeric_part(part)
        if value is None or value < 0:
            return False
        numbers.append(value)
    try:
        if len(numbers) == 1:
            if numbers[0] > 0xFFFFFFFF:
                return False
            addr = ipaddress.IPv4Address(numbers[0])
        elif len(numbers) == 2:
            a, b = numbers
            if a > 0xFF or b > 0xFFFFFF:
                return False
            addr = ipaddress.IPv4Address((a << 24) | b)
        elif len(numbers) == 3:
            a, b, c = numbers
            if a > 0xFF or b > 0xFF or c > 0xFFFF:
                return False
            addr = ipaddress.IPv4Address((a << 24) | (b << 16) | c)
        else:
            if any(n > 0xFF for n in numbers):
                return False
            addr = ipaddress.IPv4Address(".".join(str(n) for n in numbers))
    except ipaddress.AddressValueError:
        return False
    return _is_blocked_ip(addr)


def _host_is_ip_literal(host: str) -> ipaddress._BaseAddress | None:
    """تحويل المضيف إلى كائن عنوان عند الإمكان وإلا إرجاع لا شيء."""
    candidate = host.strip("[]")
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def _is_blocked_ip(addr: ipaddress._BaseAddress) -> bool:
    """فحص ما إذا كان العنوان محظورًا: خاص أو حلقي أو محلي أو سحابي."""
    text = str(addr)
    if text in _CLOUD_METADATA_IPS:
        return True
    # عناوين الحلقة الراجعة والخاصة والمحجوزة والرابط المحلي كلها محظورة.
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_reserved
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_unspecified
    )


def is_safe_url(url: str) -> bool:
    """تحديد ما إذا كان العنوان صالحًا للجلب الخارجي الصريح فقط."""
    if not isinstance(url, str) or not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    # البروتوكولات المسموحة فقط هي HTTP وHTTPS الصريحة.
    if parsed.scheme.lower() not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    # منع بيانات الاعتماد المضمنة في العنوان.
    if (
        parsed.username
        or parsed.password
        or "@" in parsed.netloc.split("@")[0]
        and "@" in url.split("://", 1)[1].split("/", 1)[0]
    ):
        return False
    # منع أسماء المضيفين المحليين صراحة قبل تحليل العناوين.
    if host in ("localhost", "localhost.", "metadata.google.internal"):
        return False
    # منع مسارات UNC وملفات Windows المحلية المتنكرة.
    lowered = url.strip().lower()
    if lowered.startswith(("file:", "ftp:", "gopher:", "dict:", "ldap:")):
        return False
    if host.endswith(".internal") or host.endswith(".local"):
        return False
    # فحص القيم العددية مباشرة عند كون المضيف عنوان IP حرفيًا.
    literal = _host_is_ip_literal(host)
    if literal is not None and _is_blocked_ip(literal):
        return False
    # كشف التمويه العددي (2130706433 هو 127.0.0.1) قبل السماح.
    if _host_is_blocked_numeric(host):
        return False
    return True


def assert_safe_url(url: str) -> None:
    """رفع خطأ نطاق عند محاولة تمرير عنوان غير آمن."""
    from atlas.intake.errors import UnsafeUrlError

    if not is_safe_url(url):
        raise UnsafeUrlError(f"refused unsafe or non-http(s) url: {url!r}")
