from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ModelKind = Literal["image", "prompt-rewriter", "upscale", "analysis"]
UpdateKind = Literal["new-version", "new-revision"]
CompatibilityState = Literal["compatible", "dependency-update-required", "unknown"]


@dataclass(frozen=True)
class ModelSpec:
    family: str
    repo_id: str
    version: str
    kind: ModelKind = "image"
    backend: str = "diffusers-auto"
    required_pipeline: str | None = None
    optional: bool = False


@dataclass
class InstalledModel:
    family: str
    repo_id: str
    version: str
    revision: str
    local_path: str
    pipeline_class: str | None
    installed_at: str
    compatibility: CompatibilityState = "unknown"

    @property
    def path(self) -> Path:
        return Path(self.local_path)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "InstalledModel":
        return cls(**value)


@dataclass(frozen=True)
class ModelCandidate:
    family: str
    repo_id: str
    version: str
    revision: str
    update_kind: UpdateKind
    pipeline_class: str | None
    compatibility: CompatibilityState
    reason: str
