# بيانات المستودع

> المقابل الإنجليزي: [`docs/en/governance/repository-metadata.md`](../../en/governance/repository-metadata.md)

بيانات المستودع المقصودة، مسجَّلةً لتبقى متّسقة عبر التغييرات. وكل قيمة هنا
مكتوبة لتكون **هادئة وهندسية وقابلة للتحقق**. ولا يجوز أن يدّعي أي بند في هذه
الوثيقة قدرة لا تدعمها البيانات.

## عنوان العرض

```text
Local LLM VRAM Atlas
```

وهو اسم المستودع نفسه. بلا اختصار، وبلا رمز تعبيري، وبلا إلحاق شعار بالعنوان.
فالعنوان يسمّي الموضوع، والوصف يحمل الادعاء.

## الوصف المختصر

يعرض GitHub نحو مئة حرف قبل الاقتطاع في معظم الواجهات، لذا كُتب الوصف بحيث يتحمّل
الاقتطاع بكلفة آخر عبارة لا أولها.

```text
Evidence-aware atlas for local LLMs across 4GB, 8GB, 12GB, and 16GB VRAM tiers, with canonical model records, quantization intelligence, architecture-aware memory analysis, quality evidence, and recommendation readiness.
```

مئتان وتسع عشرة حرفًا. ويتحمّل الاقتطاع بكلفة العبارة الأخيرة التي تقول
`and recommendation readiness`، لأنّ README يذكرها صراحةً على أي حال.

**بديل أقصر**، إن أُفضّل حقلٌ واحد أقصر:

```text
Canonical, evidence-aware catalog and analysis for local LLMs across 4/8/12/16GB VRAM tiers, with memory modelling and recommendation readiness.
```

مئة وخمس وخمسون حرفًا.

## الوصف الأطول

للاستخدام في README، أو في ملف التعريف، أو في ترويسة إصدار تتّسع له المساحة.

```text
An evidence-aware atlas for local and open-weight LLMs: canonical records, quantization intelligence, architecture-aware memory analysis, quality evidence, and recommendation readiness across 4 / 8 / 12 / 16 GB VRAM tiers — reported honestly, including where the evidence is insufficient.
```

## لماذا هذا الوصف دون غيره

البدائل المرفوضة، وسبب رفض كل منها:

| المرفوض | السبب |
|---|---|
| «توصيات نماذج متحقَّق منها لكل فئة ذاكرة» | غير صحيح. التوصيات الصارمة صفر عند كل فئة. |
| «أفضل النماذج المحلية لبطاقتك» | غير صحيح وغير قابل للقياس. لا يرتّب الأطلس. |
| «قاعدة بيانات كاملة للنماذج المحلية» | غير صحيح. الكتالوج مجموعة منتقاة من 34 إصدارًا. |
| «توافق نماذج جاهز للإنتاج» | غير مستحَق. لا نشر تشغيلي ولا شهادة. |
| «نماذج مُقاسة على المقاييس» | مضلّل. 21 نتيجة تقييم، ولا واحدة منها مستقلة متعددة المصادر. |
| «حاسبة VRAM بدقة 100%» | غير صحيح، وهو عكس أطروحة المشروع بالضبط. |

أقوى ما في الوصف أن الأطلس **واعٍ بالأدلة**. وهذا صحيح، وقابل للتحقق، وهو
المساهمة الفعلية للمشروع.

## الوسوم

تُطبَّق هذه الوسوم العشرون. والعشرون هو الحد الأقصى الحالي في GitHub.

```text
local-llm
llm
vram
gguf
quantization
model-catalog
memory-analysis
inference
llama-cpp
open-weight-models
benchmarking
recommendation-system
ai-infrastructure
model-intelligence
metadata
json-schema
catalog
documentation
bilingual
research
```

مبررات التغطية:

| الوسم | سبب استحقاقه |
|---|---|
| `local-llm` و`llm` | الموضوع المباشر. |
| `vram` | المحور المنظِّم للمشروع كله. |
| `gguf` و`quantization` | صيغة المُخرج السائدة وجوهر التحليل. |
| `model-catalog` و`catalog` و`metadata` | المُخرَج مجموعة بيانات منتقاة. |
| `memory-analysis` | يختلف عن `vram`: المنهجية نمذجة ذاكرة. |
| `inference` و`llama-cpp` | سياق بيئة التشغيل الذي يستهدفه نموذج الذاكرة. |
| `open-weight-models` | الفئة المستهدَفة. |
| `benchmarking` و`research` | انضباط الأدلة؛ دقيق رغم خلوّه من نتائج مستقلة. |
| `recommendation-system` | نوع المُخرَج المُعلن. |
| `ai-infrastructure` و`model-intelligence` | قابلية الاكتشاف. |
| `json-schema` | ثمانية عشر مخططًا مُصدَّرًا تمثّل عقدًا حقيقيًا. |
| `json-schema` | ثمانية عشر مخططًا مُصدَرًا تمثّل عقدًا حقيقيًا. |

ومستبعدة عمدًا: `cuda` و`nvidia` و`huggingface`، لأن وسوم البائعين توحي بانتماء
ينفيه المشروع صراحةً؛ وكذلك `arabic` أو `rtl` لأنها تضيّق المشروع بدل أن تصفه.

## الصفحة الرئيسية

تُترك فارغة. لا يُنشر أي موقع على GitHub،، والإشارة إلى موضع غير منشور أسوأ
من تركه بلا ضبط.

## رؤية المستودع

```text
PRIVATE
```

 والرؤية ليست تفضيلًا في البيانات الوصفية، بل بوابة إصدار. انظر ملاحظة الحالة في
الـREADME.

## المعاينة الاجتماعية

مصدر اللافتة هو `assets/branding/banner.svg`. وتتطلب ميزة المعاينة الاجتماعية في
GitHub صورة نقطية، لذا يكون تصدير ملف PNG أو JPG بأبعاد 1280 × 640 إجراءً يخصّ
المالك، لا تغييرًا في المستودع. وأمر التصدير موثَّق في
[`assets/branding/brand-guidelines.md`](../../../assets/branding/brand-guidelines.md).

## صيانة هذه الوثيقة

تُحدَّث هذه الوثيقة كلما تغيّر نطاق البيانات جوهريًا، مثلًا إذا تغيّر عدد النماذج
تغيّرًا ملموسًا، أو إذا أصبحت التوصيات الصارمة غير صفرية. وإذا اختلفت الأرقام هنا
عن الأرقام في README، فـREADME هو الخاطئ ويجب تصحيحه من الكتالوج، لا العكس.

وتُتحقَّق الأرقام الحيّة بالأوامر:

```bash
python -m atlas.cli.main catalog stats
python -m atlas.cli.main recommend tier --tier 8
python -m atlas.cli.main closure readiness
```
