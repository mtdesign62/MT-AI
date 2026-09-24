from __future__ import annotations

from PIL import Image

from mt_ai.prompts import ProtectionOptions, RenderIntent, build_prompt


def build_enhance_prompt(user_prompt: str = "") -> str:
    return build_prompt(
        RenderIntent(
            mode="Enhance",
            user_prompt=user_prompt or "Improve realism, materials, lighting and fine detail only",
            geometry_strength=98,
            mood="Natural",
            protections=ProtectionOptions(),
        )
    )


def prepare_enhance_input(image: Image.Image) -> Image.Image:
    return image.convert("RGB")
