from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from huggingface_hub import HfApi, snapshot_download, try_to_load_from_cache

from mt_ai.config import AppPaths, SettingsStore

from .provider import HuggingFaceQwenProvider
from .registry import BUILTIN_MODELS, DEFAULT_IMAGE_MODEL, DEFAULT_PROMPT_REWRITER
from .schemas import InstalledModel, ModelCandidate, ModelSpec

ProgressCallback = Callable[[str], None]


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value)


class ModelManager:
    """Installs model revisions side-by-side and switches active model atomically."""

    MANIFEST = "mt_ai_model.json"

    def __init__(
        self,
        paths: AppPaths | None = None,
        settings: SettingsStore | None = None,
        provider: HuggingFaceQwenProvider | None = None,
    ) -> None:
        self.paths = (paths or AppPaths.default()).ensure()
        self.settings = settings or SettingsStore(self.paths)
        self.provider = provider or HuggingFaceQwenProvider()
        self._api = HfApi()

    def family_path(self, family: str) -> Path:
        path = self.paths.models / family
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def family_root(self) -> Path:
        return self.family_path("qwen-image")

    def _write_manifest(self, model: InstalledModel) -> None:
        Path(model.local_path, self.MANIFEST).write_text(
            json.dumps(model.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _read_manifest(self, path: Path) -> InstalledModel | None:
        manifest = path / self.MANIFEST
        if not manifest.exists():
            return None
        try:
            return InstalledModel.from_dict(json.loads(manifest.read_text(encoding="utf-8")))
        except Exception:
            return None

    def list_installed(self, family: str = "qwen-image") -> list[InstalledModel]:
        root = self.family_path(family)
        result: list[InstalledModel] = []
        for manifest in root.glob(f"**/{self.MANIFEST}"):
            item = self._read_manifest(manifest.parent)
            if item:
                result.append(item)
        result.sort(key=lambda m: (m.version, m.installed_at), reverse=True)
        return result

    def active(self, family: str = "qwen-image") -> InstalledModel | None:
        data = self.settings.load()
        active_path = data.get("active_models", {}).get(family)
        if family == "qwen-image" and not active_path:
            active_path = data.get("active_model_path")
        if active_path:
            model = self._read_manifest(Path(active_path))
            if model:
                return model

        # Recover gracefully after settings loss/upgrades: use a single registered
        # model, or discover the official model in the local Hugging Face cache.
        installed = self.list_installed(family)
        if len(installed) == 1:
            self.activate(installed[0])
            return installed[0]
        cached = self.discover_cached(family)
        if cached is not None:
            self.activate(cached)
            return cached
        return None

    def discover_cached(self, family: str) -> InstalledModel | None:
        """Register an already-downloaded official model from the local HF cache only."""
        spec = BUILTIN_MODELS.get(family)
        if spec is None:
            return None
        marker = "model_index.json" if spec.family == DEFAULT_IMAGE_MODEL.family else "system_prompt.txt"
        try:
            cached = try_to_load_from_cache(spec.repo_id, marker)
        except Exception:
            return None
        if not isinstance(cached, str):
            return None
        try:
            return self.import_existing(Path(cached).parent)
        except (FileNotFoundError, ValueError):
            return None

    def install_spec(
        self,
        spec: ModelSpec = DEFAULT_IMAGE_MODEL,
        *,
        revision: str | None = None,
        progress: ProgressCallback | None = None,
    ) -> InstalledModel:
        info = self._api.model_info(spec.repo_id, revision=revision)
        resolved_revision = info.sha
        return self._download(
            family=spec.family,
            repo_id=spec.repo_id,
            version=spec.version,
            revision=resolved_revision,
            pipeline_class=spec.required_pipeline,
            progress=progress,
        )

    def install_candidate(
        self, candidate: ModelCandidate, *, progress: ProgressCallback | None = None
    ) -> InstalledModel:
        return self._download(
            family=candidate.family,
            repo_id=candidate.repo_id,
            version=candidate.version,
            revision=candidate.revision,
            pipeline_class=candidate.pipeline_class,
            progress=progress,
            compatibility=candidate.compatibility,
        )

    def _download(
        self,
        *,
        family: str,
        repo_id: str,
        version: str,
        revision: str,
        pipeline_class: str | None,
        progress: ProgressCallback | None,
        compatibility: str = "unknown",
    ) -> InstalledModel:
        target = self.family_path(family) / _safe_slug(repo_id) / revision[:12]
        existing = self._read_manifest(target)
        if existing:
            return existing
        target.mkdir(parents=True, exist_ok=True)
        if progress:
            progress(f"Downloading {repo_id}@{revision[:12]}...")
        snapshot_download(
            repo_id=repo_id,
            revision=revision,
            local_dir=target,
            resume_download=True,
        )
        model_index = target / "model_index.json"
        if model_index.exists():
            try:
                pipeline_class = json.loads(model_index.read_text(encoding="utf-8")).get(
                    "_class_name", pipeline_class
                )
            except json.JSONDecodeError:
                pass
        installed = InstalledModel(
            family=family,
            repo_id=repo_id,
            version=version,
            revision=revision,
            local_path=str(target),
            pipeline_class=pipeline_class,
            installed_at=datetime.now(timezone.utc).isoformat(),
            compatibility=compatibility,
        )
        self._write_manifest(installed)
        if progress:
            progress("Download complete")
        return installed

    @staticmethod
    def _resolve_existing_snapshot(source: str | Path) -> Path:
        """Resolve a Qwen model folder or Hugging Face cache root to a usable snapshot."""
        path = Path(source).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(str(path))

        def is_model_dir(candidate: Path) -> bool:
            is_image = (candidate / "model_index.json").is_file()
            is_rewriter = (candidate / "system_prompt.txt").is_file() and (
                (candidate / "config.json").is_file()
                or (candidate / "processor_config.json").is_file()
                or (candidate / "preprocessor_config.json").is_file()
            )
            return is_image or is_rewriter

        if is_model_dir(path):
            return path

        candidates: list[Path] = []
        seen: set[Path] = set()
        for marker in ("model_index.json", "system_prompt.txt"):
            for marker_path in path.glob(f"**/{marker}"):
                candidate = marker_path.parent
                if candidate in seen or ".offload" in candidate.parts:
                    continue
                seen.add(candidate)
                if is_model_dir(candidate):
                    candidates.append(candidate)
        if not candidates:
            raise ValueError(
                "No supported Qwen Image 2.1 or PE-I2I snapshot was found in the selected folder. "
                "You may select the model folder, snapshots folder, or its Hugging Face cache parent."
            )
        candidates.sort(
            key=lambda p: (
                "snapshots" in p.parts,
                max(
                    (p / name).stat().st_mtime
                    for name in ("model_index.json", "system_prompt.txt")
                    if (p / name).exists()
                ),
            ),
            reverse=True,
        )
        return candidates[0]

    def import_existing(self, source: str | Path) -> InstalledModel:
        """Register an existing local Qwen image or PE-I2I snapshot without copying it."""
        path = self._resolve_existing_snapshot(source)
        model_index = path / "model_index.json"
        if model_index.exists():
            try:
                metadata = json.loads(model_index.read_text(encoding="utf-8"))
            except Exception as exc:
                raise ValueError(f"Invalid model_index.json: {exc}") from exc
            pipeline_class = metadata.get("_class_name")
            if pipeline_class != DEFAULT_IMAGE_MODEL.required_pipeline:
                raise ValueError(
                    f"Expected {DEFAULT_IMAGE_MODEL.required_pipeline}, found {pipeline_class or 'unknown pipeline'}"
                )
            spec = DEFAULT_IMAGE_MODEL
        elif (path / "system_prompt.txt").exists():
            spec = DEFAULT_PROMPT_REWRITER
            pipeline_class = None
        else:
            raise ValueError("Selected folder is not a supported MT AI Qwen model")

        revision = path.name
        installed = InstalledModel(
            family=spec.family,
            repo_id=spec.repo_id,
            version=spec.version,
            revision=revision,
            local_path=str(path),
            pipeline_class=pipeline_class,
            installed_at=datetime.now(timezone.utc).isoformat(),
            compatibility="compatible",
        )
        self._write_manifest(installed)
        return installed

    def activate(self, model: InstalledModel) -> None:
        if not model.path.exists():
            raise FileNotFoundError(model.local_path)
        data = self.settings.load()
        active_models = dict(data.get("active_models", {}))
        previous_models = dict(data.get("previous_models", {}))
        previous = active_models.get(model.family)
        if previous and previous != model.local_path:
            previous_models[model.family] = previous
        active_models[model.family] = model.local_path
        data["active_models"] = active_models
        data["previous_models"] = previous_models
        if model.family == "qwen-image":
            data["active_model_path"] = model.local_path
            if previous:
                data["previous_model_path"] = previous
        self.settings.save(data)

    def rollback(self, family: str = "qwen-image") -> InstalledModel:
        data = self.settings.load()
        active_models = dict(data.get("active_models", {}))
        previous_models = dict(data.get("previous_models", {}))
        previous = previous_models.get(family)
        if family == "qwen-image" and not previous:
            previous = data.get("previous_model_path")
        if not previous:
            raise RuntimeError("No previous model is available for rollback")
        model = self._read_manifest(Path(previous))
        if not model:
            raise RuntimeError("Previous model metadata is missing")
        current = active_models.get(family)
        if family == "qwen-image" and not current:
            current = data.get("active_model_path")
        active_models[family] = previous
        if current:
            previous_models[family] = current
        data["active_models"] = active_models
        data["previous_models"] = previous_models
        if family == "qwen-image":
            data["active_model_path"] = previous
            if current:
                data["previous_model_path"] = current
        self.settings.save(data)
        return model

    def check_updates(self) -> list[ModelCandidate]:
        active = self.active()
        if active is None:
            info = self._api.model_info(DEFAULT_IMAGE_MODEL.repo_id)
            active_repo = DEFAULT_IMAGE_MODEL.repo_id
            active_version = DEFAULT_IMAGE_MODEL.version
            active_revision = info.sha
        else:
            active_repo = active.repo_id
            active_version = active.version
            active_revision = active.revision
        return self.provider.build_update_candidates(
            active_repo_id=active_repo,
            active_version=active_version,
            active_revision=active_revision,
        )
