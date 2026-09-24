from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# PyInstaller evaluates relative script paths from the .spec directory.
# Resolve the repository root explicitly so CI and local Windows builds behave the same.
project_root = Path(SPECPATH).resolve().parent

hiddenimports = []
datas = []
binaries = []
for pkg in ["huggingface_hub", "transformers", "diffusers"]:
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
