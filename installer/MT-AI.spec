from pathlib import Path

from PyInstaller.utils.hooks import collect_all

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
    name="MT-AI",
    console=False,
)
