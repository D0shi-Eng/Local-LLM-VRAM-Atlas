"""أدوات اختبار مشتركة: عميل وهمي ولقطات خام تركيبية دون شبكة."""

from __future__ import annotations

from types import SimpleNamespace


class FakeHfApi:
    """بديل وهمي لواجهة HfApi يسجل الوسائط ولا يتصل بالشبكة."""

    def __init__(self, info=None, error=None) -> None:
        """تثبيت نتيجة أو خطأ مسبق مع سجل استدعاءات فارغ."""
        self._info = info
        self._error = error
        self.calls: list[dict] = []

    def model_info(self, repo_id, **kwargs):
        """تسجيل الوسائط ثم إرجاع اللقطة أو رفع الخطأ المثبت."""
        self.calls.append({"repo_id": repo_id, **kwargs})
        if self._error is not None:
            raise self._error
        return self._info


def make_info(**overrides):
    """بناء كائن معلومات نموذج تركيبي بقيم افتراضية صالحة."""
    base = {
        "tags": ["license:apache-2.0", "text-generation"],
        "card_data": {"license": "apache-2.0", "language": "en", "base_model": "org/base-7b"},
        "config": {"architectures": ["LlamaForCausalLM"], "max_position_embeddings": 8192},
        "transformers_info": None,
        "siblings": [
            {"rfilename": "model-Q4_K_M.gguf", "size": 4670000000, "lfs": {"oid": "abc"}},
            {"rfilename": "README.md", "size": 5000, "lfs": None},
        ],
        "gated": False,
        "private": False,
        "disabled": False,
        "sha": "a" * 40,
        "author": "fixture-author",
        "pipeline_tag": "text-generation",
        "library_name": "transformers",
        "safetensors": {"total": 7500000000},
        "gguf": None,
        "downloads": 1234,
        "likes": 56,
        "base_models": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def minimal_info(**overrides):
    """بناء كائن معلومات فقير بالبيانات لاختبار حالات النقص."""
    base = {
        "tags": [],
        "card_data": {},
        "config": None,
        "transformers_info": None,
        "siblings": [],
        "gated": False,
        "private": False,
        "disabled": False,
        "sha": "b" * 40,
        "author": None,
        "pipeline_tag": None,
        "library_name": None,
        "safetensors": None,
        "gguf": None,
        "downloads": None,
        "likes": None,
        "base_models": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def fetched_raw(repo_id="fixture-org/fixture-model", **overrides):
    """جلب لقطة خام تركيبية عبر العميل الوهمي."""
    from atlas.intake.hf_client import HuggingFaceSourceClient

    info = overrides.pop("info", make_info(**overrides))
    client = HuggingFaceSourceClient(api=FakeHfApi(info=info))
    return client.fetch(repo_id)
