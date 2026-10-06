# عرض فئات VRAM

> متحفظ. حجم الملف ≠ VRAM. مؤهَّل ≠ موصى به.

## اللغة

عناوين صفحات الفئات مثل «أطلس VRAM بسعة 8GB»، وليست «كل النماذج التي تعمل
على 8GB»، إلا إذا استوفى كل إدخال المعيار فعلًا. الأقسام تفصل
`estimated_fit` و `indeterminate_fit` و `estimated_not_fit` و
`insufficient_evidence` و `unsupported` (مع `verified_fit` فقط عند وجود دليل
قياس خارجي بشروط كاملة؛ أطلس لا يقيس أثناء الاستقبال).

## المنهج

المصنف المعتمد من المرحلتين 2 و3 فقط (`src/atlas/vram/classifier.py`) مع
تقديرات ثابتة مُنطَقة (`src/atlas/memory/estimator.py`، خط أساس 8K). لا يوجد
اختصار `artifact_size < tier_size → fits`؛ اختبارات الانحدار تحرسه. معاملات
MoE النشطة لا تُستخدم كأوزان مقيمة أبدًا.

## القياسات الخارجية

تُخزَّن ولا تُجرى. يحفظ كل منها المصدر والمراجعة والـartifact ووقت التشغيل
+ الإصدار وGPU والسياق والدفعة وصيغة KV والإزاحة والمرحلة وVRAM المبلغ عنها
والمصدر وتاريخ الرصد. ادعاءات «يستخدم 7GB» المبهمة تبقى ضعيفة أو لا تُستخدم
لترقية الفئة. `atlas_measured` محظور بنيويًا أثناء الاستقبال).

## ذات صلة

- `static-vram-classification.md`، `vram-methodology.md`
- `external-measurement-evidence.md`، `static-memory-modeling.md`
