from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class GeometryAnalysis:
    edge_map: np.ndarray
    line_count: int
    vertical_lines: int
    horizontal_lines: int
    diagonal_lines: int


def _classify_angle(x1: int, y1: int, x2: int, y2: int) -> str:
    angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) % 180
    if angle < 12 or angle > 168:
        return "horizontal"
    if 78 < angle < 102:
        return "vertical"
    return "diagonal"


def _normalize_hough_lines(lines: np.ndarray | None) -> np.ndarray:
    """Return HoughLinesP output as a stable N x 4 array across OpenCV versions."""
    if lines is None:
        return np.empty((0, 4), dtype=np.int32)
    arr = np.asarray(lines)
    if arr.size == 0:
        return np.empty((0, 4), dtype=np.int32)
    if arr.size % 4 != 0:
        raise ValueError(f"Unexpected HoughLinesP output shape: {arr.shape}")
    return arr.reshape(-1, 4)


def analyze_geometry(image: Image.Image) -> GeometryAnalysis:
    arr = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 70, 160)
    min_len = max(25, min(image.size) // 12)
    raw_lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=50,
        minLineLength=min_len,
        maxLineGap=12,
    )
    lines = _normalize_hough_lines(raw_lines)
    counts = {"vertical": 0, "horizontal": 0, "diagonal": 0}
    for line in lines:
        counts[_classify_angle(*map(int, line.tolist()))] += 1
    return GeometryAnalysis(
        edge_map=edges,
        line_count=sum(counts.values()),
        vertical_lines=counts["vertical"],
        horizontal_lines=counts["horizontal"],
        diagonal_lines=counts["diagonal"],
    )
