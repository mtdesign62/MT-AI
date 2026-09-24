from packaging.version import Version

from mt_ai.models.registry import is_official_qwen_image_release, qwen_image_version


def test_qwen_version_parser():
    assert qwen_image_version("Qwen/Qwen-Image-2.1") == Version("2.1")
    assert qwen_image_version("Qwen/Qwen-Image-3.0") == Version("3.0")
    assert qwen_image_version("Qwen/Qwen-Image-2.1-PE-I2I") is None
    assert is_official_qwen_image_release("Qwen/Qwen-Image-2.2")
