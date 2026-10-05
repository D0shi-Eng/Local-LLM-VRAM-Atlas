"""خط أنابيب الاستقبال المعياري: من المعرف العام إلى سجل معتمد."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atlas.intake.errors import IntakeRejectedError, SchemaValidationFailedError
from atlas.intake.hf_client import HuggingFaceSourceClient, validate_repo_id
from atlas.intake.models import IntakeOutcome, RawModelMetadata
from atlas.intake.normalize import model_id_from_repo, normalize
from atlas.intake.provenance import build_evidence_records, build_source_records
from atlas.intake.store import atomic_write_json
from atlas.validation.validator import validate_record

# جذر المشروع ومجلدات الكتالوج الافتراضية داخل المسار المعتمد فقط.
REPO_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = REPO_ROOT / "catalog" / "models"
SOURCES_DIR = REPO_ROOT / "catalog" / "sources"
EVIDENCE_DIR = REPO_ROOT / "catalog" / "evidence"


@dataclass(frozen=True)
class IntakeRequest:
    """طلب استقبال واحد بمعرف عام ومراجعة مطلوبة."""

    repo_id: str
    revision: str = "main"
    dry_run: bool = True
    allow_update: bool = False


class IntakePipeline:
    """منسق مراحل الاستقبال مع فشل صريح بدل السجل المضلل."""

    def __init__(self, client: HuggingFaceSourceClient | None = None) -> None:
        """حقن عميل المصدر لعزل الشبكة عن منطق النطاق."""
        self._client = client or HuggingFaceSourceClient()

    def build(self, repo_id: str, *, revision: str = "main") -> IntakeOutcome:
        """تنفيذ كامل المراحل حتى التحقق دون أي كتابة دائمة."""
        validate_repo_id(repo_id)
        raw: RawModelMetadata = self._client.fetch(repo_id, revision=revision)
        return self.build_from_raw(raw)

    def build_from_raw(self, raw: RawModelMetadata) -> IntakeOutcome:
        """بناء النتيجة من لقطة خام موجودة لضمان الحتمية والاختبار."""
        record, warnings = normalize(raw)
        license_status = str(record.get("license", {}).get("verification_status", "unknown"))
        source_records = build_source_records(raw)
        evidence_records = build_evidence_records(raw, license_status)
        # ربط السجل المعياري بالأدلة المبنية من نفس اللقطة.
        record["verification"] = {
            "status": str(record.get("verification", {}).get("status", "publisher_claim")),
            "evidence_ids": [str(item["evidence_id"]) for item in evidence_records],
        }
        model_errors = validate_record(record, "model")
        if model_errors:
            details = "; ".join(f"{err.path}: {err.message}" for err in model_errors)
            raise SchemaValidationFailedError(
                f"canonical record failed schema validation: {details}"
            )
        for source in source_records:
            source_errors = validate_record(source, "source")
            if source_errors:
                details = "; ".join(f"{err.path}: {err.message}" for err in source_errors)
                raise SchemaValidationFailedError(f"source record failed validation: {details}")
        for evidence in evidence_records:
            evidence_errors = validate_record(evidence, "evidence")
            if evidence_errors:
                details = "; ".join(f"{err.path}: {err.message}" for err in evidence_errors)
                raise SchemaValidationFailedError(f"evidence record failed validation: {details}")
        state = self._decide_state(raw, record)
        return IntakeOutcome(
            model_record=record,
            source_records=source_records,
            evidence_records=evidence_records,
            intake_state=state,
            warnings=tuple(warnings),
        )

    def _decide_state(self, raw: RawModelMetadata, record: dict) -> str:
        """تحديد حالة الاستقبال الصادقة دون استخدام حالات محظورة."""
        if raw.private or (raw.gated and raw.resolved_revision is None):
            return "blocked"
        license_status = str(record.get("license", {}).get("verification_status", "unknown"))
        if license_status == "unknown":
            return "pending_license"
        if (
            record.get("architecture_type") == "unknown"
            and record.get("total_parameters_b") is None
        ):
            return "pending_metadata"
        if record.get("catalog_status") == "pending_metadata":
            return "pending_metadata"
        return "metadata_verified"

    def execute(
        self,
        request: IntakeRequest,
        *,
        models_dir: Path | None = None,
        sources_dir: Path | None = None,
        evidence_dir: Path | None = None,
    ) -> IntakeOutcome:
        """تنفيذ الطلب مع الالتزام بقاعدة التجربة الجافة أولًا."""
        outcome = self.build(request.repo_id, revision=request.revision)
        if request.dry_run:
            return outcome
        self.persist(
            outcome,
            request,
            models_dir=models_dir,
            sources_dir=sources_dir,
            evidence_dir=evidence_dir,
        )
        return outcome

    def persist(
        self,
        outcome: IntakeOutcome,
        request: IntakeRequest,
        *,
        models_dir: Path | None = None,
        sources_dir: Path | None = None,
        evidence_dir: Path | None = None,
    ) -> dict[str, str]:
        """كتابة ذرية مع حماية السجل القديم من الاستبدال الصامت."""
        models = Path(models_dir) if models_dir is not None else MODELS_DIR
        sources = Path(sources_dir) if sources_dir is not None else SOURCES_DIR
        evidences = Path(evidence_dir) if evidence_dir is not None else EVIDENCE_DIR
        model_id = str(outcome.model_record["model_id"])
        target = models / f"{model_id}.json"
        if target.is_file():
            existing = json.loads(target.read_text(encoding="utf-8"))
            existing_revision = self._existing_revision(existing)
            new_revision = self._new_revision(outcome)
            if existing_revision != new_revision and not request.allow_update:
                raise IntakeRejectedError(
                    f"refusing to overwrite {model_id} with a new revision "
                    f"({existing_revision!r} -> {new_revision!r}) without --allow-update"
                )
            if existing == outcome.model_record:
                return {"model": str(target), "action": "idempotent_hit"}
        atomic_write_json(target, outcome.model_record)
        written: dict[str, str] = {"model": str(target), "action": "written"}
        self._persist_sidecars(outcome, sources_dir=sources, evidence_dir=evidences)
        return written

    def _persist_sidecars(
        self,
        outcome: IntakeOutcome,
        *,
        sources_dir: Path,
        evidence_dir: Path,
    ) -> None:
        """كتابة سجلات المصدر والدليل بجانب السجل المعياري."""
        for source in outcome.source_records:
            atomic_write_json(sources_dir / f"{source['source_id']}.json", source)
        for evidence in outcome.evidence_records:
            atomic_write_json(evidence_dir / f"{evidence['evidence_id']}.json", evidence)

    @staticmethod
    def _existing_revision(existing: dict[str, Any]) -> str | None:
        """استخراج المراجعة المحفوظة من سجل قديم دون تخمين."""
        quantization = existing.get("quantization") or {}
        return quantization.get("source_revision")

    @staticmethod
    def _new_revision(outcome: IntakeOutcome) -> str | None:
        """استخراج المراجعة الجديدة من نتيجة الاستقبال الحالية."""
        quantization = outcome.model_record.get("quantization") or {}
        return quantization.get("source_revision")

    @staticmethod
    def model_path_for(repo_id: str, *, models_dir: Path | None = None) -> Path:
        """المسار الحتمي لسجل المستودع داخل الكتالوج المحلي."""
        base = Path(models_dir) if models_dir is not None else MODELS_DIR
        return base / f"{model_id_from_repo(repo_id)}.json"
