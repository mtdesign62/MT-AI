from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from mt_ai.config import AppPaths
from mt_ai.hardware import detect_hardware
from mt_ai.models.manager import ModelManager
from mt_ai.version import APP_VERSION


def _pkg(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"
    except Exception:
        return "unknown"


def diagnostics_text() -> str:
    hw = detect_hardware()
    manager = ModelManager()
    active = manager.active()
    rewriter = manager.active("qwen-image-prompt-rewriter")
    paths = AppPaths.default().ensure()
    rows = [
        f"MT AI: {APP_VERSION}",
        f"OS: {hw.os}",
        f"Python: {hw.python}",
        f"GPU: {hw.gpu_name or 'Not available'}",
        f"CUDA: {hw.cuda_version or 'Not available'}",
        f"VRAM free/total MB: {hw.vram_free_mb}/{hw.vram_total_mb}",
        f"RAM free/total MB: {hw.ram_available_mb}/{hw.ram_total_mb}",
        f"Disk free MB: {hw.disk_free_mb}",
        f"Recommended profile: {hw.recommended_profile}",
        f"Active model: {active.repo_id if active else 'Not installed/activated'}",
        f"Active revision: {active.revision if active else '-'}",
        f"Model path: {active.local_path if active else '-'}",
        f"Prompt rewriter: {rewriter.repo_id if rewriter else 'Not installed/activated'}",
        f"Prompt rewriter path: {rewriter.local_path if rewriter else '-'}",
        f"torch: {_pkg('torch')}",
        f"diffusers: {_pkg('diffusers')}",
        f"transformers: {_pkg('transformers')}",
        f"accelerate: {_pkg('accelerate')}",
        f"Log file: {paths.logs / 'mt-ai.log'}",
    ]
    return "\n".join(rows)
