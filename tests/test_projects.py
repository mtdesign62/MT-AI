from pathlib import Path

from PIL import Image

from mt_ai.config import AppPaths
from mt_ai.projects import ProjectManager


def make_paths(root: Path) -> AppPaths:
    return AppPaths(root, root / "models", root / "projects", root / "cache", root / "logs", root / "settings.json").ensure()


def test_project_create_and_render(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (64, 64), "white").save(source)
    manager = ProjectManager(make_paths(tmp_path / "data"))
    project = manager.create("Test", source)
    out = manager.save_render(project, Image.new("RGB", (64, 64), "black"), {"seed": 42})
    assert out.exists()
    assert len(manager.list_projects()) == 1
