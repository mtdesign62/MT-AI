from packaging.version import Version

from mt_ai.models.provider import HuggingFaceQwenProvider, RemoteModelInfo


class FakeProvider(HuggingFaceQwenProvider):
    def __init__(self):
        pass

    def list_official_releases(self, limit=50):
        return [
            RemoteModelInfo(
                repo_id="Qwen/Qwen-Image-3.0",
                version=Version("3.0"),
                revision="c" * 40,
                pipeline_class="QwenImage30Pipeline",
                compatibility="dependency-update-required",
                reason="needs newer diffusers",
            ),
            RemoteModelInfo(
                repo_id="Qwen/Qwen-Image-2.1",
                version=Version("2.1"),
                revision="b" * 40,
                pipeline_class="QwenImage21Pipeline",
                compatibility="compatible",
                reason="ok",
            ),
        ]


def test_detects_future_version_and_same_version_revision():
    provider = FakeProvider()
    candidates = provider.build_update_candidates(
        active_repo_id="Qwen/Qwen-Image-2.1",
        active_version="2.1",
        active_revision="a" * 40,
    )
    assert any(c.version == "3.0" and c.update_kind == "new-version" for c in candidates)
    assert any(c.version == "2.1" and c.update_kind == "new-revision" for c in candidates)
