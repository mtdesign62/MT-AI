from __future__ import annotations

from mt_ai.hardware import detect_hardware
from mt_ai.models.manager import ModelManager
from mt_ai.version import APP_VERSION


def diagnostics_text() -> str:
    hw = detect_hardware()
    manager = ModelManager()
    active = manager.active()
    rows = [
        f"MT AI: {APP_VERSION}",
        f"OS: {hw.os}",
        f"Python: {hw.python}",
        f"GPU: {hw.gpu_name or 'Not available'}",
        f"CUDA: {hw.cuda_version or 'Not available'}",
        f"VRAM total MB: {hw.vram_total_mb}",
        f"RAM total MB: {hw.ram_total_mb}",
        f"Recommended profile: {hw.recommended_profile}",
        f"Active model: {active.repo_id if active else 'Not installed/activated'}",
        f"Active revision: {active.revision if active else '-'}",
    ]
    return "\n".join(rows)
