# منهجية عروض الكتالوج

> مُوَلَّدة من السجلات المعيارية. لا تحرير يدوي. ترتيب حتمي.

## الفئات

`catalog/views/4gb|8gb|12gb|16gb/` يحتوي كل منها `view.json` مع
`index.en.md` / `index.ar.md`. الأقسام حالات توافق صريحة:

توافق مؤكد، توافق مقدَّر، مرشحات غير محسومة، لا يتوافق، أدلة غير كافية
(مع `unsupported` عند الاقتضاء).

ملف artifacts بحجم 6 GiB لا يصبح «نموذج 8GB» بالحجم وحده. الحد الأدنى وحده
دون حد علوي موثوق يبقى `indeterminate`/`insufficient` ولا يصبح أبدًا
`estimated_fit`. انظر `static-vram-classification.md` و
`src/atlas/catalog/tiering.py`.

نطاقات التخزين (`remote_artifact_under_8_gib`) مساعدات تصفح فقط ولا تدعي
توافق VRAM أبدًا.

## العروض الخاصة

`high-compression/`، `native-low-bit/`، `ternary/`، `uncensored/`،
`abliterated/`، `heretic/` — كل منها `view.json` مع صفحات EN/AR من نفس
البيانات. انظر `special-variant-classification.md`.

## البيان

`catalog/manifest.json` (`catalog_version 0.4.0`، قبل 1.0) يسرد المعرفات
حتميًا للمستهلكين دون تكرار السجلات الكاملة.

## ذات صلة

- `vram-tier-methodology.md`، `runtime-support-methodology.md`
- `generated-documentation-policy.md`
