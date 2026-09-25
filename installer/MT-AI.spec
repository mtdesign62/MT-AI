from importlib.metadata import distributions
from pathlib import Path
import os

from PyInstaller.utils.hooks import collect_all, copy_metadata

project_root = Path(SPECPATH).resolve().parent

hiddenimports = []
datas = []
binaries = []

# The local-Qwen runtime must be part of the packaged application.
# Model weights stay separate and are downloaded by Model Manager.
for pkg in [
    "huggingface_hub",
    "torch",
    "transformers",
    "accelerate",
    "safetensors",
    "diffusers",
]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# Diffusers, Transformers and their dependencies perform runtime
# importlib.metadata.version(...) checks. PyInstaller can freeze the Python
# modules while omitting *.dist-info, which makes an installed dependency
# appear missing. Preserve metadata for all packages in the proven build env
# so the frozen app sees the same dependency graph as the source environment.
_seen_metadata = set()
for dist in distributions():
    name = dist.metadata.get("Name")
    if not name:
        continue
    key = name.lower()
    if key in _seen_metadata:
        continue
    _seen_metadata.add(key)
    try:
        datas += copy_metadata(name)
    except Exception:
        pass

a = Analysis(
    [str(project_root / "mt_ai" / "app.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=os.environ.get("MT_AI_EXE_NAME", "MT-AI"),
    console=False,
)
