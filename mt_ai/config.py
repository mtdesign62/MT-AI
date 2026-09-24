from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _user_data_root() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "MT AI"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "mt-ai"


@dataclass(frozen=True)
class AppPaths:
    root: Path
    models: Path
    projects: Path
    cache: Path
    logs: Path
    settings: Path

    @classmethod
    def default(cls) -> "AppPaths":
        root = _user_data_root()
        return cls(
            root=root,
            models=root / "models",
            projects=root / "projects",
            cache=root / "cache",
            logs=root / "logs",
            settings=root / "settings.json",
        )

    def ensure(self) -> "AppPaths":
        for path in (self.root, self.models, self.projects, self.cache, self.logs):
            path.mkdir(parents=True, exist_ok=True)
        return self


class SettingsStore:
    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = (paths or AppPaths.default()).ensure()

    def load(self) -> dict[str, Any]:
        if not self.paths.settings.exists():
            return {}
        try:
            return json.loads(self.paths.settings.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, data: dict[str, Any]) -> None:
        self.paths.settings.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.paths.settings.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.paths.settings)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self.load()
        data[key] = value
        self.save(data)
