"""الكتابة الذرية: بناء السجل في الذاكرة ثم استبدال الهدف دون ملف ناقص."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def canonical_json_bytes(record: dict) -> bytes:
    """ترميز معياري حتمي بترتيب ثابت وترميز UTF-8 وسطر نهائي."""
    text = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)
    return (text + "\n").encode("utf-8")


def atomic_write_json(target: Path, record: dict) -> None:
    """كتابة ذرية عبر ملف مؤقت داخل المشروع ثم استبدال الهدف."""
    target = Path(target)
    if target.parent and not target.parent.is_dir():
        target.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(record)
    # الملف المؤقت داخل مجلد الهدف نفسه حتى يكون الاستبدال ذريًا.
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        try:
            Path(tmp_name).unlink(missing_ok=True)
        except OSError:
            pass
