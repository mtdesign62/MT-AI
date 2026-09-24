from datetime import datetime, timezone
from pathlib import Path

from mt_ai.config import AppPaths, SettingsStore
from mt_ai.models.manager import ModelManager
from mt_ai.models.schemas import InstalledModel


def make_paths(root: Path) -> AppPaths:
    return AppPaths(
        root=root,
        models=root / "models",
        projects=root / "projects",
        cache=root / "cache",
        logs=root / "logs",
        settings=root / "settings.json",
    ).ensure()


def test_activate_and_rollback(tmp_path):
    paths = make_paths(tmp_path)
    manager = ModelManager(paths=paths, settings=SettingsStore(paths))
    a_dir = manager.family_root / "a"
    b_dir = manager.family_root / "b"
    a_dir.mkdir(parents=True)
    b_dir.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat()
    a = InstalledModel("qwen-image", "Qwen/Qwen-Image-2.1", "2.1", "a" * 40, str(a_dir), "QwenImage21Pipeline", now)
    b = InstalledModel("qwen-image", "Qwen/Qwen-Image-3.0", "3.0", "b" * 40, str(b_dir), "QwenImage30Pipeline", now)
    manager._write_manifest(a)
    manager._write_manifest(b)
    manager.activate(a)
    manager.activate(b)
    assert manager.active().version == "3.0"
    rolled = manager.rollback()
    assert rolled.version == "2.1"
    assert manager.active().version == "2.1"
