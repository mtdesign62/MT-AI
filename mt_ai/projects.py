from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .config import AppPaths


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    path: Path


class ProjectManager:
    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = (paths or AppPaths.default()).ensure()

    def create(self, name: str, source: str | Path) -> Project:
        project_id = uuid.uuid4().hex[:12]
        root = self.paths.projects / project_id
        for sub in ("input", "analysis", "renders", "exports"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        src = Path(source)
        input_path = root / "input" / f"original{src.suffix.lower() or '.png'}"
        shutil.copy2(src, input_path)
        data = {
            "project_id": project_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": str(input_path.relative_to(root)),
            "renders": [],
        }
        self._write(root, data)
        return Project(project_id, name, root)

    def _write(self, root: Path, data: dict) -> None:
        tmp = root / "project.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(root / "project.json")

    def save_render(self, project: Project, image: Image.Image, metadata: dict) -> Path:
        data = json.loads((project.path / "project.json").read_text(encoding="utf-8"))
        index = len(data.get("renders", [])) + 1
        out = project.path / "renders" / f"render_{index:04d}.png"
        image.save(out)
        meta = out.with_suffix(".json")
        meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        data.setdefault("renders", []).append({"image": str(out.relative_to(project.path)), "metadata": str(meta.relative_to(project.path))})
        self._write(project.path, data)
        return out

    def list_projects(self) -> list[Project]:
        result = []
        for manifest in self.paths.projects.glob("*/project.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                result.append(Project(data["project_id"], data["name"], manifest.parent))
            except Exception:
                continue
        return sorted(result, key=lambda p: p.path.stat().st_mtime, reverse=True)
