# منهجية فئات VRAM

> المقابل الإنجليزي: `docs/en/methodology/vram-tier-methodology.md`

## الفئات والوحدات

فئات الأطلس الرسمية هي **4GB و8GB و12GB و16GB** (`src/atlas/vram/`). كل شيء
داخليًا بالبايت المعياري، والجيبيبايت للعرض فقط، والجيجابايت العشرية لا
تختلط بالحساب أبدًا. واسم الفئة تصنيف للمستخدم، والقيمة الحقيقية هي رقم
البايت بجانبه دائمًا. والسعة الاسمية تتبع السياسة `atlas-tier-nominal-v1`
(جيبيبايت الفئة بالبايت)، والسعة القابلة للاستخدام أدنى وستدخل لاحقًا عبر
`system_headroom_profile` معاير لا عبر ثابت خفي.

## التصنيف القائم على النطاق

لنطاق موثوق `[lower, upper]` وسعة فئة:

- `upper ≤ capacity` ← `estimated_fit`
- `lower ≤ capacity < upper` ← `indeterminate_fit`
- `lower > capacity` (حد أدنى موثوق) ← `estimated_not_fit`
- غياب حد موثوق أو بنية غير مدعومة ← `insufficient_evidence` أو `unsupported`

يتطلب `verified_fit` قياسًا حقيقيًا ولا ينتجه التقدير، ولا توجد لغة
`tight fit` حتى تُعاير سياسة هامش، ولا يُطبق هامش نسبة ثابت بصمت.

## ما ليس تصنيفًا

بايت الـartifact وحده لا ينتج حكم fit أبدًا: ملف أوزان 6 GiB يعني
`artifact_weight_storage ≈ 6 GiB` لا `Fits 8GB`. ويمنع اختبار انحدار اختصار
حجم الملف إلى Fit. وقد يبلغ المصنف عن `estimated_minimum_nominal_tier_gb`
عند سماح الأدلة، لكن **Recommended VRAM تبقى مؤجلة**
(`recommendation_headroom_status: not_calibrated`) حتى توجد قياسات تشغيل
وسياسة هامش. واستهلاك العرض والتعريف ونظام التشغيل ينتظر بدوره ملف هامش
النظام بدل رقم عالمي مخترع.
