$ErrorActionPreference = "Stop"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\pyinstaller.exe --clean --noconfirm installer\MT-AI.spec
Write-Host "Build output is under dist/. Clean-machine validation is still required."
