$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher (py.exe) was not found. Install Python 3.11 first."
}

py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
& .\.venv\Scripts\pip.exe install -r requirements\base.txt
& .\.venv\Scripts\pip.exe install -r requirements\ai.txt
& .\.venv\Scripts\pip.exe install -r requirements\dev.txt
Write-Host "MT AI environment ready. Run: .\.venv\Scripts\python.exe -m mt_ai"
