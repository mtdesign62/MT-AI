from mt_ai.inference.qwen import fit_dimensions


def test_fit_dimensions_preserves_landscape_ratio():
    w, h = fit_dimensions((1600, 900), "Standard")
    assert max(w, h) == 1536
    assert abs((w / h) - (1600 / 900)) < 0.06
    assert w % 32 == 0 and h % 32 == 0
