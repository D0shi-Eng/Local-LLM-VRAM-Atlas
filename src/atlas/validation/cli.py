"""واجهة سطر الأوامر للتحقق من سجل واحد مقابل مخططاته.

رموز الخروج: 0 عند النجاح، و1 عند فشل التحقق، و2 عند خطأ الاستخدام.
"""

from __future__ import annotations

import argparse
import sys

from atlas.validation.validator import SUPPORTED_KINDS, ValidatorUsageError, validate_file


def build_parser() -> argparse.ArgumentParser:
    """بناء محلل الوسائط الخاص بأداة التحقق."""
    parser = argparse.ArgumentParser(
        description="Validate one Atlas JSON record against its schema."
    )
    parser.add_argument(
        "--schema",
        required=True,
        choices=SUPPORTED_KINDS,
        help="Schema kind to validate against.",
    )
    parser.add_argument("--record", required=True, help="Path to the JSON record file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """نقطة الدخول: التحقق ثم طباعة الأخطاء بصيغة مقروءة."""
    args = build_parser().parse_args(argv)
    try:
        errors = validate_file(args.record, args.schema)
    except ValidatorUsageError as exc:
        print(f"ERROR {exc.path}: {exc.message}")
        return 2
    if errors:
        for error in errors:
            print(f"FAIL {error.path}: {error.message}")
        print(f"invalid: {args.record} does not conform to schema '{args.schema}'")
        return 1
    print(f"valid: {args.record} conforms to schema '{args.schema}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
