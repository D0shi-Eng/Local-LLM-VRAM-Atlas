# منهجية التكميم (Quantization)

> المقابل الإنجليزي: `docs/en/methodology/quantization-methodology.md`

## التمثيل لا التسمية الوحيدة

يُسجَّل التكميم كائنًا منظمًا — `format` و`quant_family` و`quant_name`
و`bits_per_weight` و`native_quantization` و`quantizer` و`quantizer_repo`
و`file_size_bytes` و`file_size_gib` و`split_files` و`source_revision` و`checksum` —
ولا يُختزَل في تسمية مفردة عارية.

## العائلات

تشمل تسميات العائلات المعترف بها `fp32` و`fp16` و`bf16` و`fp8` و`q8` و`q6` و`q5`
و`q4` و`iq4` و`q3` و`iq3` و`q2` و`iq2` و`iq1` و`tq` و`ternary` و`mxfp4` و`nvfp4`
و`awq` و`gptq` و`exl2` و`mlx` و`other`. هذه تسميات لا ترتيب: لا يُعامَل أعضاء
العائلات المختلفة باعتبارهم متقارنين أو متكافئين مباشرة دون دليل، ولا يُوصَف
تكميم بأنه أفضل من آخر دون إثبات.

## فئات الضغط

السلال الوصفية `native_precision` و`light_quantization` و`balanced_quantization`
و`aggressive_quantization` و`ultra_compressed` و`extreme_compression`
و`native_low_bit` تصنيف أولي لا حكم جودة مطلق. يبقى نوع التكميم الحقيقي دائمًا في
`quant_family`/`quant_name` منفصلًا عن السلة.

## النسب

تُميَّز النماذج منخفضة البتات أصليًا (المدرَّبة على عمق البتات المعلن) عن التكميم
اللاحق للتدريب عبر `native_quantization`، لأن أسئلة الاحتفاظ بالقدرات تختلف بين
الحالتين. ويجب أن يتتبع كل متغير مكمم أو معدَّل نسبه: المتغير، والنموذج المكمم،
والنموذج المعدل/المدقق، والنموذج الأساسي، وعائلة الأصل. لا يُفقَد النسب أبدًا.
