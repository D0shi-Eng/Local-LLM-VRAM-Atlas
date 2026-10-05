<!-- مولّد آلياً بواسطة خط أنابيب الإغلاق للمرحلة 6.5 - لا تُحرَّر يدوياً. أعد التوليد عبر `atlas closure views --apply`. -->
# مجموعة التوصيات الأساسية

> مشتق من سجلات الإغلاق القانونية في المرحلة 6.5. يُبلَّغ عن الأدلة الناقصة كـ
> «غير معروف»؛ أما الشعبية والحجم وحداثة الإصدار وعدد المعاملات واسم الناشر فلا
> تؤثر إطلاقاً في هذه العروض.

| المرشّح | النموذج | المُخرَج | التكميم | الفئات المستهدفة | الحالة |
|---|---|---|---|---|---|
| `core-12g-01-qwen3-8b-q6k` | `quantfactory-qwen3-8b-gguf` | `quantfactory-qwen3-8b-gguf--gguf--qwen3-8b-gguf--q6_k` | Q6_K | [12] | جاهز كمرشح |
| `core-12g-02-qwen38-27b-iq3s` | `unsloth-qwen3-8-27b-gguf` | `unsloth-qwen3-8-27b-gguf--gguf--qwen3.8-27b-ud-gguf--iq3_s` | IQ3_S | [12] | دليل الفهرسة فقط |
| `core-12g-03-gpt-oss-20b-mxfp4-gguf` | `bartowski-openai-gpt-oss-20b-gguf` | `bartowski-openai-gpt-oss-20b-gguf--gguf--openai_gpt-oss-20b-gguf--mxfp4` | MXFP_4 | [12] | دليل الفهرسة فقط |
| `core-16g-01-gpt-oss-20b-native` | `openai-gpt-oss-20b` | `openai-gpt-oss-20b--safetensors--original/model.safetensors` | native_mxfp4 | [16] | دليل الفهرسة فقط |
| `core-16g-02-qwen3-coder-30b-q3km` | `unsloth-qwen3-coder-30b-a3b-instruct-gguf` | `unsloth-qwen3-coder-30b-a3b-instruct-gguf--gguf--qwen3-coder-30b-a3b-instruct-gguf--q3_k_m` | Q3_K_M | [16] | جاهز كمرشح |
| `core-16g-03-qwen3-8b` | `qwen-qwen3-8b` | `qwen-qwen3-8b--safetensors--model.safetensors` | bf16 | [16] | دليل الفهرسة فقط |
| `core-4g-01-qwen3-0-6b` | `qwen-qwen3-0-6b` | `qwen-qwen3-0-6b--safetensors--model.safetensors` | bf16 | [4] | دليل الفهرسة فقط |
| `core-4g-02-bitnet-native` | `microsoft-bitnet-b1-58-2b-4t` | `microsoft-bitnet-b1-58-2b-4t--safetensors--model.safetensors` | native_1.58bit | [4] | دليل الفهرسة فقط |
| `core-4g-03-bitnet-gguf-i2s` | `microsoft-bitnet-b1-58-2b-4t-gguf` | `microsoft-bitnet-b1-58-2b-4t-gguf--gguf--ggml-model-i2_s.gguf` | unlabeled_gguf_variant | [4] | دليل الفهرسة فقط |
| `core-4g-04-qwen2-5-7b-iq3xs` | `bartowski-qwen2-5-7b-instruct-gguf` | `bartowski-qwen2-5-7b-instruct-gguf--gguf--qwen2.5-7b-instruct-gguf--iq3_xs` | IQ3_XS | [4] | جاهز كمرشح |
| `core-4g-05-qwen3-8b-q2k` | `quantfactory-qwen3-8b-gguf` | `quantfactory-qwen3-8b-gguf--gguf--qwen3-8b-gguf--q2_k` | Q2_K | [4] | جاهز كمرشح |
| `core-4g-06-tinyllama-1-1b` | `tinyllama-tinyllama-1-1b-chat-v1-0` | `tinyllama-tinyllama-1-1b-chat-v1-0--safetensors--model.safetensors` | bf16 | [4] | دليل الفهرسة فقط |
| `core-8g-01-qwen2-5-7b-q4km` | `bartowski-qwen2-5-7b-instruct-gguf` | `bartowski-qwen2-5-7b-instruct-gguf--gguf--qwen2.5-7b-instruct-gguf--q4_k_m` | Q4_K_M | [8] | جاهز كمرشح |
| `core-8g-02-qwen3-8b-q4km` | `quantfactory-qwen3-8b-gguf` | `quantfactory-qwen3-8b-gguf--gguf--qwen3-8b-gguf--q4_k_m` | Q4_K_M | [8] | جاهز كمرشح |
| `core-8g-03-qwen3-4b-instruct-2507` | `qwen-qwen3-4b-instruct-2507` | `qwen-qwen3-4b-instruct-2507--safetensors--model.safetensors` | bf16 | [8] | دليل الفهرسة فقط |
| `core-8g-04-phi-3-mini-4k` | `microsoft-phi-3-mini-4k-instruct` | `microsoft-phi-3-mini-4k-instruct--safetensors--model.safetensors` | bf16 | [8] | دليل الفهرسة فقط |
| `core-8g-05-ternary-bonsai-tq1` | `prism-ml-ternary-bonsai-2-27b-gguf` | `prism-ml-ternary-bonsai-2-27b-gguf--gguf--ternary-bonsai-2-27b-p.gguf--tq1_0` | TQ1_0 | [8] | دليل الفهرسة فقط |
| `core-8g-06-llama31-lexi-uncensored-q4` | `orenguteng-llama-3-1-8b-lexi-uncensored-gguf` | `orenguteng-llama-3-1-8b-lexi-uncensored-gguf--gguf--llama-3.1-8b-lexi-uncensored-gguf--q4` | Q4 | [8] | محظور |
| `core-8g-07-ternary-heretic-tq1` | `os-software-ternary-bonsai-2-27b-uncensored-heretic-gguf` | `os-software-ternary-bonsai-2-27b-uncensored-heretic-gguf--gguf--ternary-bonsai-2-27b-uncensored-heretic-p.gguf--tq1_0` | TQ1_0 | [8, 16] | دليل الفهرسة فقط |

_مولَّد من سجلات قانونية قابلة للقراءة آلياً._
