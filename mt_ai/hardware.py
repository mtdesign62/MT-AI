from __future__ import annotations

import json
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil


@dataclass(frozen=True)
class HardwareProfile:
    os: str
    python: str
    cpu: str
    ram_total_mb: int
    disk_free_mb: int
    cuda_available: bool
    cuda_version: str | None
    gpu_name: str | None
    vram_total_mb: int | None
    vram_free_mb: int | None
    recommended_profile: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def detect_hardware(path_for_disk: Path | None = None) -> HardwareProfile:
    cuda_available = False
    cuda_version = None
    gpu_name = None
    vram_total = None
    vram_free = None
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        cuda_version = getattr(torch.version, "cuda", None)
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            free, total = torch.cuda.mem_get_info(0)
            vram_free = int(free / 1024 / 1024)
            vram_total = int(total / 1024 / 1024)
    except Exception:
        pass

    ram_total = int(psutil.virtual_memory().total / 1024 / 1024)
    disk_root = path_for_disk or Path.home()
    try:
        disk_free = int(shutil.disk_usage(disk_root).free / 1024 / 1024)
    except OSError:
        disk_free = 0

    # Qwen Image 2.1 workstation support target: NVIDIA CUDA GPUs with >=12 GB VRAM.
    # Profiles are selected by available memory rather than GPU model name, so RTX 30/40/50,
    # workstation and future CUDA cards can share the same adaptive path.
    if not cuda_available or (vram_total or 0) < 11264:
        recommended = "unsupported"
    elif (vram_total or 0) < 14336:
        recommended = "low-memory-12gb"
    elif (vram_total or 0) < 20480:
        recommended = "low-memory"
    elif (vram_total or 0) < 24576:
        recommended = "balanced"
    else:
        recommended = "quality"

    return HardwareProfile(
        os=f"{platform.system()} {platform.release()}",
        python=platform.python_version(),
        cpu=platform.processor() or platform.machine(),
        ram_total_mb=ram_total,
        disk_free_mb=disk_free,
        cuda_available=cuda_available,
        cuda_version=cuda_version,
        gpu_name=gpu_name,
        vram_total_mb=vram_total,
        vram_free_mb=vram_free,
        recommended_profile=recommended,
    )
