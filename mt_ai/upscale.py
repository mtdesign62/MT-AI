from __future__ import annotations

from PIL import Image, ImageFilter


class UpscaleBackend:
    name = "abstract"

    def upscale(self, image: Image.Image, scale: int) -> Image.Image:
        raise NotImplementedError


class LanczosUpscaleBackend(UpscaleBackend):
    """Always-available fallback. Replace with a licensed AI backend without changing UI APIs."""

    name = "lanczos-fallback"

    def upscale(self, image: Image.Image, scale: int) -> Image.Image:
        if scale not in (2, 4):
            raise ValueError("scale must be 2 or 4")
        out = image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
        return out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=70, threshold=3))
