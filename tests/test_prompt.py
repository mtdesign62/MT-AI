from mt_ai.prompts import ProtectionOptions, RenderIntent, build_prompt


def test_architecture_prompt_keeps_constraints():
    text = build_prompt(
        RenderIntent(
            mode="Architecture",
            user_prompt="blue hour, only a few office windows lit",
            geometry_strength=95,
            protections=ProtectionOptions(),
        )
    )
    low = text.lower()
    assert "preserve the exact source viewpoint" in low
    assert "do not change floor count" in low
    assert "do not move doors or windows" in low
    assert "blue hour" in low


def test_masterplan_adds_plan_rule():
    text = build_prompt(RenderIntent(mode="Masterplan", user_prompt="natural", geometry_strength=98))
    assert "Keep roads, plot boundaries, building footprints" in text
