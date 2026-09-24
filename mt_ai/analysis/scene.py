from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class SceneAnalysis:
    mode_hint: str
    width: int
    height: int
    aspect_ratio: float
    brightness: float
    contrast: float
    edge_density: float
    lighting_hint: str
    geometry_complexity: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (
            f"{self.mode_hint}; {self.width}x{self.height}; {self.lighting_hint}; "
            f"geometry {self.geometry_complexity}; edge density {self.edge_density:.2f}"
        )


class SceneAnalyzer:
    """Fast deterministic V1 analyzer. Later versions can plug in a local VLM backend."""

    def analyze(self, image: Image.Image | str | Path, mode_hint: str = "Architecture") -> SceneAnalysis:
        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")
        else:
            image = image.convert("RGB")
        arr = np.asarray(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        brightness = float(gray.mean() / 255.0)
        contrast = float(gray.std() / 255.0)
        edges = cv2.Canny(gray, 80, 160)
        edge_density = float(np.count_nonzero(edges) / edges.size)
        if brightness < 0.27:
            lighting = "dark / night-like source"
        elif brightness > 0.72:
            lighting = "bright daylight-like source"
        else:
            lighting = "mid-level / mixed lighting source"
        if edge_density > 0.18:
            complexity = "high"
        elif edge_density > 0.09:
            complexity = "medium"
        else:
            complexity = "low"
        return SceneAnalysis(
            mode_hint=mode_hint,
            width=image.width,
            height=image.height,
            aspect_ratio=image.width / max(1, image.height),
            brightness=brightness,
            contrast=contrast,
            edge_density=edge_density,
            lighting_hint=lighting,
            geometry_complexity=complexity,
            confidence=0.55,
        )
