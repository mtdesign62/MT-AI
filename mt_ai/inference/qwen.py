from __future__ import annotations

import inspect
import time
from dataclasses import dataclass
from typing import Any

from PIL import Image

from mt_ai.models.schemas import InstalledModel

from .types import RenderRequest, RenderResult


class InferenceUnavailableError(RuntimeError):
    pass


class InferenceOOMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadOptions:
    memory_profile: str = "balanced"


def _round_to(value: int, multiple: int = 32) -> int:
    return max(multiple, int(round(value / multiple) * multiple))


def fit_dimensions(size: tuple[int, int], quality: str) -> tuple[int, int]:
    """Preserve aspect ratio while targeting a practical render envelope."""
    w, h = size
    if quality == "Draft":
        long_side = 1024
    elif quality == "Standard":
        long_side = 1536
    else:
        long_side = 2048
    scale = long_side / max(w, h)
    target_w = _round_to(max(256, int(w * scale)))
    target_h = _round_to(max(256, int(h * scale)))
    return target_w, target_h


class QwenEngine:
    """Diffusers-backed image editing engine with conservative future-pipeline compatibility."""

    def __init__(self, model: InstalledModel) -> None:
        self.model = model
        self.pipe: Any = None
        self.loaded_profile: str | None = None

    def load(self, memory_profile: str = "balanced") -> None:
        try:
            import torch
            from diffusers import DiffusionPipeline
        except ImportError as exc:
            raise InferenceUnavailableError(
                "AI dependencies are missing. Install requirements/ai.txt."
            ) from exc
        if not torch.cuda.is_available():
            raise InferenceUnavailableError("Qwen Image local rendering currently requires NVIDIA CUDA")

        kwargs: dict[str, Any] = {"torch_dtype": torch.bfloat16, "local_files_only": True, "low_cpu_mem_usage": True}
        # A 16 GB workstation can become unresponsive if pipeline loading is allowed to
        # consume all system RAM/VRAM. Low-memory mode uses a conservative device map
        # and an on-disk offload folder so Diffusers/Accelerate can spill safely.
        if memory_profile == "low-memory":
            from pathlib import Path

            offload_dir = Path(self.model.local_path).parent / ".offload"
            offload_dir.mkdir(parents=True, exist_ok=True)
            kwargs.update(
                {
                    "device_map": "balanced",
                    "max_memory": {0: "13GiB", "cpu": "20GiB"},
                    "offload_folder": str(offload_dir),
                    "offload_state_dict": True,
                }
            )
        self.pipe = DiffusionPipeline.from_pretrained(self.model.local_path, **kwargs)
        if memory_profile == "low-memory":
            # device_map already placed/offloaded components during loading. Calling
            # enable_model_cpu_offload() as well would fight Accelerate hooks.
            pass
        else:
            self.pipe.to("cuda")
        if hasattr(self.pipe, "set_progress_bar_config"):
            self.pipe.set_progress_bar_config(disable=False)
        self.loaded_profile = memory_profile

    def unload(self) -> None:
        self.pipe = None
        try:
            import gc
            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        self.loaded_profile = None

    def _filtered_call_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.pipe is None:
            return kwargs
        signature = inspect.signature(self.pipe.__call__)
        if any(p.kind == p.VAR_KEYWORD for p in signature.parameters.values()):
            return kwargs
        allowed = set(signature.parameters)
        return {k: v for k, v in kwargs.items() if k in allowed}

    def render(self, request: RenderRequest) -> RenderResult:
        try:
            import torch
        except ImportError as exc:
            raise InferenceUnavailableError("PyTorch is not installed") from exc
        if self.pipe is None or self.loaded_profile != request.memory_profile:
            self.unload()
            self.load(request.memory_profile)

        width, height = (
            (request.width, request.height)
            if request.width and request.height
            else fit_dimensions(request.source.size, request.quality)
        )
        generator = torch.Generator(device="cuda").manual_seed(request.seed)
        kwargs = {
            "prompt": request.prompt,
            "image": request.source.convert("RGB"),
            "num_inference_steps": request.steps,
            "generator": generator,
            "width": int(width),
            "height": int(height),
        }
        call_kwargs = self._filtered_call_kwargs(kwargs)
        start = time.perf_counter()
        try:
            output = self.pipe(**call_kwargs)
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower():
                try:
                    torch.cuda.empty_cache()
                finally:
                    raise InferenceOOMError(
                        "CUDA out of memory. Switch to Low Memory or a smaller quality preset."
                    ) from exc
            raise
        duration = time.perf_counter() - start
        image = output.images[0].convert("RGB")
        return RenderResult(
            image=image,
            seed=request.seed,
            steps=request.steps,
            width=image.width,
            height=image.height,
            duration_seconds=duration,
            model_repo_id=self.model.repo_id,
            model_revision=self.model.revision,
            metadata={"memory_profile": request.memory_profile, "quality": request.quality},
        )
