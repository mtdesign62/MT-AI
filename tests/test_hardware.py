from mt_ai.hardware import detect_hardware


def test_hardware_smoke():
    hw = detect_hardware()
    assert hw.ram_total_mb > 0
    assert hw.recommended_profile in {"quality", "balanced", "low-memory", "unsupported"}
