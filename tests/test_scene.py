from PIL import Image

from mt_ai.analysis.scene import SceneAnalyzer


def test_scene_analysis_basic():
    image = Image.new("RGB", (800, 600), "white")
    result = SceneAnalyzer().analyze(image, "Interior")
    assert result.mode_hint == "Interior"
    assert result.width == 800
    assert result.height == 600
    assert result.brightness > 0.9
