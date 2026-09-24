from mt_ai.prompt_rewriter import _extract_json


def test_extract_rewrite_json():
    text = 'thinking... {"rewritten_prompt":"warm morning", "wh_ratio":"", "ratio_follow":"<image1>"}'
    result = _extract_json(text)
    assert result["rewritten_prompt"] == "warm morning"
