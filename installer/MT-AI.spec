# PyInstaller skeleton. Validate on Windows after the CUDA/Qwen environment is proven.
from PyInstaller.utils.hooks import collect_all

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
    ["mt_ai/app.py"],
    pathex=["."],
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
