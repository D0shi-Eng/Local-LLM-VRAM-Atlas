# منهجية تأهيل الكتالوج

> الحالة: لقطة أولية منتقاة. بيانات وصفية فقط. لا ترتيب ولا نقاط.

## ماذا تعني «مؤهَّل»

«مؤهَّل» تعني أن أطلس يملك بيانات وصفية موثوقة كافية لإدراج النموذج وفق
قواعد الكتالوج الحالية. ولا تعني الأفضل أو الموصى به أو الآمن أو الأسرع
أو المتحقق بالكامل من VRAM.

- `qualified` تُخزَّن كـ `catalog_status: verified`
- `qualified_with_limitations` تُخزَّن كـ `catalog_status: experimental`
  مع توثيق كل قيد صراحة (بنية جزئية، ترخيص مخصص، دعم تشغيل مجهول،
  توافق VRAM غير محسوم، مراجعة غير محلولة).
- `blocked` / `rejected` / `deprecated` تحفظ السبب؛ لا حذف صامت.

تُعاد استخدام تعدادات `model.schema.json` الحالية؛ انظر
`src/atlas/catalog/qualification.py`. لا انحراف في المخطط.

## الأدلة المطلوبة

الهوية، المصدر (مع مراجعة محلولة أو قيد موثق)، حالة الترخيص، حالة النسب،
بيانات Artifacts، حالة التكميم/الصيغة، حالة البنية، النسب الموثق. لا تُخترع
بيانات ناقصة للوصول إلى `qualified`.

## ذات صلة

- `model-intake.md`، `metadata-verification.md`، `evidence-confidence-methodology.md`
- `static-vram-classification.md` (حالات التوافق تبقى متميزة)
- `uncensored-classification.md` (ادعاءات المحاذاة تبقى ادعاءات)
