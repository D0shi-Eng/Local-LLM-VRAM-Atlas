# سياسة التوثيق المُوَلَّد (المرحلة 4)

> السجلات المعيارية تقود العروض. Markdown مُوَلَّد وليس قاعدة بيانات ثانية.

## القواعد

- `catalog/models/*.json` و `catalog/artifacts/*.json` و
  `catalog/manifest.json` هي مصدر الحقيقة (تُتحقق بـ JSON Schema حيث يوجد
  مخطط).
- `catalog/views/**/*.md` و `catalog/views/**/*.json` تحمل علامات التوليد
  (`مُوَلَّد بواسطة خط أنابيب كتالوج أطلس — لا تحرر يدويًا`) وتعليمات إعادة
  التوليد (`atlas catalog views` / خط التعبئة).
- نفس البيانات تنتج EN (`index.en.md`) و AR (`index.ar.md`)؛ لا تباين يدوي.
  المصطلحات التقنية (GGUF و EXL2 و AWQ و GPTQ و KV Cache و MoE و VRAM) تبقى
  إنجليزية مع شرح عربي.
- نفس المدخلات → نفس البايتات (`sort_keys=True` ومعرفات مرتبة وترتيب حتمي)
  باستثناء `generated_at` الموثق.
- لا تحرير يدوي للملفات المُوَلَّدة. أصلح المُوَلِّد أو البيانات المعيارية
  ثم أعد التوليد.

## ذات صلة

- `provenance-methodology.md`، `metadata-verification.md`
