# سير عمل توليد بيانات الكتالوج

> المقابل الإنجليزي: [`docs/en/workflows/catalog-data-generation.md`](../../en/workflows/catalog-data-generation.md)
>
> المخططات معروضة في الوثيقة الإنجليزية عن قصد، لوضوح المصطلحات الهندسية.
> ولكل شكل شرح عربي في [فهرس الأشكال](../../diagrams/README.md).

## النطاق

تصف هذه الوثيقة كيف تُنتَج مجموعة بيانات المستودع وتوثيقاته من السجلات القانونية،
وكيف يبدو سطح المستودع المنتقى.

القاعدة الحاكمة بسيطة ومطلقة:

> **الكتالوج القانوني هو مصدر الحقيقة. كل ملف Markdown وكل عرض JSON مولَّد منه
> ولا يُعدَّل يدويًا أبدًا.**

## الشكل ٨ — من السجلات القانونية إلى العروض المنشورة

المخطط بالإنجليزية في
[catalog-data-generation.md](../../en/workflows/catalog-data-generation.md).

## المولَّد مقابل المكتوب يدويًا

| الأصل | المالك | يُعاد توليده بـ |
|---|---|---|
| `catalog/views/**/index.en.md` | **مولَّد** | `atlas catalog views` و`atlas quality views` و`atlas closure views` |
| `catalog/views/**/index.ar.md` | **مولَّد** | الأوامر نفسها، من الحمولة القانونية نفسها |
| `catalog/views/**/view.json` | **مولَّد** | الأوامر نفسها |
| `catalog/manifest.json` | **مولَّد** | `atlas catalog manifest` |
| `catalog/quality/profiles/**` | **مولَّد** | `atlas quality snapshot --apply` |
| `catalog/quality/retention/**` | **مولَّد** | `atlas quality snapshot --apply` |
| `catalog/closure/readiness.json` | **مولّد** | `atlas closure readiness --apply` |
| `catalog/models/**` و`catalog/artifacts/**` | قانوني | يكتبه الاستقبال، سجلًا لكل مُخرَج |
| `docs/en/**` و`docs/ar/**` | مكتوب يدويًا | غير مولَّد؛ ويجب أن يستند إلى البيانات القانونية |
| `README.md` و`README_AR.md` | مكتوب يدويًا | غير مولَّد |
| `assets/branding/**` | مكتوب يدويًا | غير مولَّد |

## التوليد ثنائي اللغة

تُولَّد العروض الإنجليزية والعربية من **حمولة قانونية واحدة** في العملية نفسها.
وهذه ضمانة بنيوية لا خطوة مراجعة: لا يمكن للغتين أن تتباعدا، لأن لهما مصدرًا واحدًا،
ولأن التوليد يجري لهما معًا.
والحكم نفسه ينطبق على التوثيق المكتوب يدويًا، حيث يفرض اختبار أن لكل وثيقة إنجليزية
مقابلًا عربيًا وبنية عناوين مطابقة.

## الشكل ٩ — معمارية معلومات المستودع

المخطط بالإنجليزية في
[catalog-data-generation.md](../../en/workflows/catalog-data-generation.md).

## ما هو غائب عمدًا من الشجرة المنشورة

تاريخ الهندسة الداخلي ليس إغفالًا، بل هو مستبعَد بقصد:

| المستبعَد | السبب |
|---|---|
| `docs/phases/**` | تقارير البناء الداخلية وتقارير الإغلاق وجرد التسليم. ليست توثيقًا عامًا. |
| `catalog/refresh/**` | سجلات تشغيل متقلبة؛ يُعاد توليدها عند الحاجة. |
| `catalog/checkpoints/**` | حالة اكتشاف داخلية مؤقتة. |
| `catalog/changes/**` | يوم تغييرات تشغيلي؛ يُعاد توليده، ويُحدث ضجيجًا بوصفه تاريخًا. |
| `catalog/release-candidate-data-manifest.json` | بيان تشغيلي يحمل مسارًا محليًا مطلقًا. |
| `catalog/closure/external/bonsai-existing-server.json` | رصد لجهاز المالك، بما فيه معرّف العملية والمنفذ. |

ولا يلزم أيٌّ من هذه المسارات لقراءة مجموعة البيانات المنشورة أو التحقق منها أو
إعادة توليدها.

## إعادة توليد مجموعة البيانات

```bash
python -m atlas.cli.main catalog views            # عروض الفئات والمحاور
python -m atlas.cli.main quality snapshot         # الملفات والاحتفاظ والفجوات والبيان
python -m atlas.cli.main quality views            # عروض الجودة بالعربية والإنجليزية
python -m atlas.cli.main closure views            # عروض الإغلاق بالعربية والإنجليزية
python -m atlas.cli.main catalog stats            # الإحصاءات حسب الصيغة وعائلة التكميم
```

كل أمر توليد يعمل في وضع تجريبي افتراضيًا؛ أضِف `--apply` للكتابة.

## قراءة إضافية

- [نظرة عامة على الكتالوج](../catalog/catalog-overview.md)
- [معمارية المستودع](../architecture/repository-architecture.md)
- [سياسة التوثيق المولَّد](../methodology/generated-documentation-policy.md)
- [منهجية عروض الكتالوج](../methodology/catalog-views.md)
