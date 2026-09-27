from __future__ import annotations


def adaptive_memory_profile(
    recommended_profile: str,
    total_vram_mb: int | None,
    free_vram_mb: int | None,
) -> str:
    """Downgrade conservatively when runtime free VRAM is under pressure."""
    if recommended_profile == "unsupported":
        return recommended_profile
    if total_vram_mb is None or free_vram_mb is None or total_vram_mb <= 0:
        return recommended_profile
    if total_vram_mb < 14336:
        return "low-memory-12gb"

    ratio = free_vram_mb / total_vram_mb
    if free_vram_mb < 4096 or ratio < 0.25:
        return "low-memory-12gb"
    if free_vram_mb < 6144 or ratio < 0.38:
        return "low-memory"
    return recommended_profile


def _round32(value: float) -> int:
    return max(512, int(round(value / 32.0)) * 32)


def oom_retry_size(size: tuple[int, int]) -> tuple[int, int]:
    """Return one smaller aspect-preserving internal size for controlled OOM recovery."""
    width, height = size
    return _round32(width * 0.8), _round32(height * 0.8)
