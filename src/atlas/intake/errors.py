"""أخطاء النطاق الخاصة بعملية الاستقبال مع دلالات فشل مميزة."""

from __future__ import annotations


class IntakeError(Exception):
    """خطأ أساس لكل أعطال الاستقبال مع حالة آلية قابلة للتسجيل."""

    status: str = "unknown"

    def __init__(self, message: str) -> None:
        """بناء الخطأ مع رسالة بشرية قابلة للسجل."""
        super().__init__(message)
        self.message = message


class NotFoundError(IntakeError):
    """تعذر العثور على المستودع لدى المصدر (HTTP 404)."""

    status = "not_found"


class RevisionNotFoundError(IntakeError):
    """تعذر العثور على المراجعة المطلوبة داخل المستودع."""

    status = "not_found"


class NetworkTimeoutError(IntakeError):
    """انتهت مهلة الشبكة دون رد من المصدر."""

    status = "network_timeout"


class RateLimitedError(IntakeError):
    """رفض المصدر الطلب بسبب تجاوز معدل الطلبات (HTTP 429)."""

    status = "rate_limited"


class AuthenticationRequiredError(IntakeError):
    """تتطلب البيانات اعتمادًا ولا يجوز تجاوزها دون تسجيل صريح."""

    status = "authentication_required"


class GatedResourceError(IntakeError):
    """المورد مقيد بشروط ولا يتوفر عبر الوصول المجهول."""

    status = "gated"


class InvalidMetadataError(IntakeError):
    """بيانات المصدر مشوهة ولا تصلح للتطبيع."""

    status = "invalid_metadata"


class SchemaValidationFailedError(IntakeError):
    """فشل السجل المرشح في التحقق من مخطط أطلس."""

    status = "schema_validation_failed"


class SourceUnavailableError(IntakeError):
    """المصدر غير متاح مؤقتًا أو دائمًا دون تشخيص أدق."""

    status = "source_unavailable"


class UnsupportedMetadataError(IntakeError):
    """نوع بيانات غير مدعوم دون فقدان الحقيقة."""

    status = "unsupported_metadata"


class WeightDownloadBlockedError(IntakeError):
    """منع محاولة تنزيل وزن نموذج كخط دفاع متعمد."""

    status = "blocked"


class UnsafeUrlError(IntakeError):
    """رفض عنوان غير آمن قبل أي جلب شبكي."""

    status = "blocked"


class IntakeRejectedError(IntakeError):
    """رفض الاستقبال لسبب موثق دون اختراع بيانات."""

    status = "rejected"
