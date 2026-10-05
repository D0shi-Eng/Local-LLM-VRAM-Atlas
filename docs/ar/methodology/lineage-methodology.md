# منهجية السلالة

> المقابل الإنجليزي: `docs/en/methodology/lineage-methodology.md`

## العلاقات

المرحلة الأولى تدعم: `base_model` و`fine_tune_of` و`quantized_from`
و`derived_from` و`format_variant_of` و`official_variant_of`. كل حافة تسجل
مصدرها؛ وحواف `model_card_metadata` تبقى `publisher_declared` ولا تُرقى
تلقائيًا إلى `atlas_verified` أبدًا.

## عتبة الدليل

بيانات `base_model` في بطاقة النموذج تكفي لتسجيل حافة نسب معلنة من الناشر —
ولا تكفي للتحقق منها. تشابه الأسماء وحده (`SomeModel-27B-Q4` الذي يبدو
مكممًا) إشارة مرشحة `inferred_candidate_signal` في أحسن الأحوال، وليس حقيقة
متحققًا منها أبدًا، ولا عدد معاملات ولا ترخيصًا ولا نموذج أساس.

## أصناف الهوية

`same_repository_same_revision` و`same_repository_new_revision` و`mirror`
و`format_variant` و`quantized_variant` و`fine_tune` و`official_sibling`
و`third_party_derivative` و`same_family` و`unrelated_same_name`.
النماذج من عائلة واحدة ليست تكرارًا صراحة.

## اتجاه السلسلة

```text
النموذج الأصلي ← النموذج المضبوط ← المتغير المكمم ← الملف المحدد
```

كل حافة تحمل مصدرها حتى تستطيع المراحل القادمة ربط الترخيص والسلوك
والعتاد بالملف الصحيح.
