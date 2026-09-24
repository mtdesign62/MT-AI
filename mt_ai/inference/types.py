from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from PIL import Image

MemoryProfile = Literal["quality", "balanced", "low-memory"]
QualityMode = Literal["Draft", "Standard", "High", "Ultra"]


@dataclass
class RenderRequest:
    source: Image.Image
    prompt: str
    seed: int = 42
    steps: int = 40
    quality: QualityMode = "Standard"
    memory_profile: MemoryProfile = "balanced"
    width: int | None = None
    height: int | None = None


@dataclass
class RenderResult:
    image: Image.Image
    seed: int
    steps: int
    width: int
    height: int
    duration_seconds: float
    model_repo_id: str
    model_revision: str
    metadata: dict = field(default_factory=dict)

    def serializable_metadata(self) -> dict:
        data = asdict(self)
        data.pop("image", None)
        return data
