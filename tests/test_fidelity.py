from PIL import Image, ImageDraw

from mt_ai.analysis.fidelity import compare_source_and_render


def architecture_box(offset=0):
    image = Image.new("RGB", (512, 384), "white")
    d = ImageDraw.Draw(image)
    d.rectangle((60 + offset, 60, 450 + offset, 330), outline="black", width=8)
    for x in (110, 210, 310, 410):
        d.rectangle((x + offset, 120, x + 40 + offset, 190), outline="black", width=5)
    return image


def test_identical_has_high_fidelity():
    src = architecture_box()
    report = compare_source_and_render(src, src.copy())
    assert report.overall_score > 0.95


def test_large_shift_reduces_fidelity():
    src = architecture_box()
    shifted = architecture_box(35)
    report = compare_source_and_render(src, shifted)
    assert report.overall_score < 0.9
