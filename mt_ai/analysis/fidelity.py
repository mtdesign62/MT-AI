from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np
from PIL import Image

from .geometry import analyze_geometry


@dataclass(frozen=True)
class FidelityReport:
    edge_score: float
    orientation_score: float
    structure_score: float
    overall_score: float

    def to_dict(self) -> dict:
        return asdict(self)


def _edge_f1(a: np.ndarray, b: np.ndarray, tolerance: int = 2) -> float:
    a = a > 0
    b = b > 0
    if not a.any() and not b.any():
        return 1.0
    kernel = np.ones((tolerance * 2 + 1, tolerance * 2 + 1), np.uint8)
    a_d = cv2.dilate(a.astype(np.uint8), kernel) > 0
    b_d = cv2.dilate(b.astype(np.uint8), kernel) > 0
    p = float((a & b_d).sum()) / max(1.0, float(a.sum()))
    r = float((b & a_d).sum()) / max(1.0, float(b.sum()))
    return 2 * p * r / max(1e-8, p + r)


def _orientation_vector(g) -> np.ndarray:
    vec = np.array([g.vertical_lines, g.horizontal_lines, g.diagonal_lines], dtype=np.float32)
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm else vec


def compare_source_and_render(source: Image.Image, render: Image.Image) -> FidelityReport:
    target_size = source.size
    render = render.convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
    src_g = analyze_geometry(source.convert("RGB"))
    out_g = analyze_geometry(render)
    edge = _edge_f1(src_g.edge_map, out_g.edge_map)
    a = _orientation_vector(src_g)
    b = _orientation_vector(out_g)
    orientation = float(np.clip(np.dot(a, b), 0.0, 1.0)) if (a.any() and b.any()) else 1.0
    structure = 0.72 * edge + 0.28 * orientation
    overall = structure
    return FidelityReport(
        edge_score=round(edge, 4),
        orientation_score=round(orientation, 4),
        structure_score=round(structure, 4),
        overall_score=round(overall, 4),
    )
