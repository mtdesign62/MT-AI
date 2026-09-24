from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from huggingface_hub import HfApi, hf_hub_download
from packaging.version import Version

from .registry import qwen_image_version
from .schemas import CompatibilityState, ModelCandidate


@dataclass(frozen=True)
class RemoteModelInfo:
    repo_id: str
    version: Version
    revision: str
    pipeline_class: str | None
    compatibility: CompatibilityState
    reason: str


class HuggingFaceQwenProvider:
    """Discovers official Qwen Image releases and validates local Diffusers support."""

    def __init__(self, api: HfApi | None = None) -> None:
        self.api = api or HfApi()

    def _pipeline_class(self, repo_id: str, revision: str | None = None) -> str | None:
        path = hf_hub_download(repo_id=repo_id, filename="model_index.json", revision=revision)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data.get("_class_name")

    @staticmethod
    def _compatibility(pipeline_class: str | None) -> tuple[CompatibilityState, str]:
        if not pipeline_class:
            return "unknown", "model_index.json has no _class_name"
        try:
            diffusers = importlib.import_module("diffusers")
        except ImportError:
            return "dependency-update-required", "Diffusers is not installed"
        if hasattr(diffusers, pipeline_class):
            return "compatible", f"{pipeline_class} is available in installed Diffusers"
        return (
            "dependency-update-required",
            f"Installed Diffusers does not expose {pipeline_class}",
        )

    def list_official_releases(self, limit: int = 50) -> list[RemoteModelInfo]:
        rows: list[RemoteModelInfo] = []
        models: Iterable = self.api.list_models(
            author="Qwen",
            search="Qwen-Image",
            sort="lastModified",
            direction=-1,
            limit=limit,
            full=True,
        )
        for item in models:
            repo_id = getattr(item, "id", None) or getattr(item, "modelId", None)
            if not repo_id:
                continue
            version = qwen_image_version(repo_id)
            if version is None:
                continue
            revision = getattr(item, "sha", None)
            if not revision:
                try:
                    revision = self.api.model_info(repo_id).sha
                except Exception:
                    continue
            try:
                pipeline_class = self._pipeline_class(repo_id, revision)
                compatibility, reason = self._compatibility(pipeline_class)
            except Exception as exc:
                pipeline_class = None
                compatibility = "unknown"
                reason = f"Could not inspect model metadata: {exc}"
            rows.append(
                RemoteModelInfo(
                    repo_id=repo_id,
                    version=version,
                    revision=revision,
                    pipeline_class=pipeline_class,
                    compatibility=compatibility,
                    reason=reason,
                )
            )
        rows.sort(key=lambda row: row.version, reverse=True)
        return rows

    def build_update_candidates(
        self,
        *,
        active_repo_id: str,
        active_version: str,
        active_revision: str,
    ) -> list[ModelCandidate]:
        current = Version(active_version)
        result: list[ModelCandidate] = []
        for row in self.list_official_releases():
            if row.version > current:
                result.append(
                    ModelCandidate(
                        family="qwen-image",
                        repo_id=row.repo_id,
                        version=str(row.version),
                        revision=row.revision,
                        update_kind="new-version",
                        pipeline_class=row.pipeline_class,
                        compatibility=row.compatibility,
                        reason=row.reason,
                    )
                )
            elif row.repo_id == active_repo_id and row.revision != active_revision:
                result.append(
                    ModelCandidate(
                        family="qwen-image",
                        repo_id=row.repo_id,
                        version=str(row.version),
                        revision=row.revision,
                        update_kind="new-revision",
                        pipeline_class=row.pipeline_class,
                        compatibility=row.compatibility,
                        reason=row.reason,
                    )
                )
        return result
