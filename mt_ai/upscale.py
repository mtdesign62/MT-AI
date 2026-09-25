from __future__ import annotations

from PIL import Image, ImageFilter


def _round32(value: float) -> int:
    return max(256, int(round(value / 32.0)) * 32)


def smart_generation_size(target: tuple[int, int], profile: str, quality: str) -> tuple[int, int]:
    """Choose a diffusion-safe internal size; final output is resized to the exact target."""
    tw, th = target
    limits = {
        "low-memory-12gb": {"Draft": 896, "Standard": 1024, "High": 1152, "Ultra": 1280},
        "low-memory": {"Draft": 1024, "Standard": 1152, "High": 1344, "Ultra": 1536},
        "balanced": {"Draft": 1152, "Standard": 1344, "High": 1536, "Ultra": 1792},
        "quality": {"Draft": 1280, "Standard": 1536, "High": 1792, "Ultra": 2048},
    }
    max_side = limits.get(profile, limits["low-memory-12gb"]).get(quality, 1024)
    if max(tw, th) <= max_side:
        return _round32(tw), _round32(th)
    scale = max_side / max(tw, th)
    return _round32(tw * scale), _round32(th * scale)


class UpscaleBackend:
    name = "abstract"

    def upscale(self, image: Image.Image, scale: int) -> Image.Image:
        raise NotImplementedError

    def resize_to(self, image: Image.Image, size: tuple[int, int]) -> Image.Image:
        raise NotImplementedError


class LanczosUpscaleBackend(UpscaleBackend):
    """Always-available high-quality finalizer; keeps diffusion away from unsafe 2K/4K VRAM loads."""

    name = "lanczos-smart-finalizer"

    def resize_to(self, image: Image.Image, size: tuple[int, int]) -> Image.Image:
        if image.size == size:
            return image
        out = image.resize(size, Image.Resampling.LANCZOS)
        if size[0] > image.width or size[1] > image.height:
            out = out.filter(ImageFilter.UnsharpMask(radius=0.8, percent=45, threshold=3))
        return out

    def upscale(self, image: Image.Image, scale: int) -> Image.Image:
        if scale not in (2, 4):
            raise ValueError("scale must be 2 or 4")
        return self.resize_to(image, (image.width * scale, image.height * scale))
