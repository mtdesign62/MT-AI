from mt_ai.memory import adaptive_memory_profile, oom_retry_size


def test_12gb_class_always_uses_conservative_profile():
    assert adaptive_memory_profile("low-memory-12gb", 12288, 9000) == "low-memory-12gb"


def test_runtime_pressure_downgrades_profile():
    assert adaptive_memory_profile("low-memory", 16384, 3500) == "low-memory-12gb"
    assert adaptive_memory_profile("balanced", 22528, 5500) == "low-memory"


def test_oom_retry_size_reduces_size_and_keeps_alignment():
    retry = oom_retry_size((1536, 864))
    assert retry[0] < 1536 and retry[1] < 864
    assert retry[0] % 32 == 0 and retry[1] % 32 == 0
