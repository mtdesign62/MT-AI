from mt_ai.inference.qwen import fit_dimensions
from mt_ai.upscale import smart_generation_size


def test_fit_dimensions_preserves_landscape_ratio():
    w, h = fit_dimensions((1600, 900), "Standard")
    assert max(w, h) == 1536
    assert abs((w / h) - (1600 / 900)) < 0.06
    assert w % 32 == 0 and h % 32 == 0


def test_smart_generation_size_clamps_when_free_vram_is_low():
    roomy = smart_generation_size(
        (3840, 2160), "low-memory", "Ultra", free_vram_mb=12000
    )
    pressured = smart_generation_size(
        (3840, 2160), "low-memory", "Ultra", free_vram_mb=3500
    )
    assert max(roomy) == 1536
    assert max(pressured) == 1024
    assert pressured[0] % 32 == 0 and pressured[1] % 32 == 0
