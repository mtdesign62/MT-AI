from __future__ import annotations

import re
from packaging.version import InvalidVersion, Version

from .schemas import ModelSpec

DEFAULT_IMAGE_MODEL = ModelSpec(
    family="qwen-image",
    repo_id="Qwen/Qwen-Image-2.1",
    version="2.1",
    kind="image",
    backend="diffusers-auto",
    required_pipeline="QwenImage21Pipeline",
)

DEFAULT_PROMPT_REWRITER = ModelSpec(
    family="qwen-image-prompt-rewriter",
    repo_id="Qwen/Qwen-Image-2.1-PE-I2I",
    version="2.1",
    kind="prompt-rewriter",
    optional=True,
)

BUILTIN_MODELS = {
    DEFAULT_IMAGE_MODEL.family: DEFAULT_IMAGE_MODEL,
    DEFAULT_PROMPT_REWRITER.family: DEFAULT_PROMPT_REWRITER,
}

_QWEN_IMAGE_VERSION = re.compile(r"^Qwen/Qwen-Image-(\d+(?:\.\d+)*)$")


def qwen_image_version(repo_id: str) -> Version | None:
    match = _QWEN_IMAGE_VERSION.match(repo_id)
    if not match:
        return None
    try:
        return Version(match.group(1))
    except InvalidVersion:
        return None


def is_official_qwen_image_release(repo_id: str) -> bool:
    return qwen_image_version(repo_id) is not None
