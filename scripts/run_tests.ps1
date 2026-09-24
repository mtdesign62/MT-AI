$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "."
python -m compileall -q mt_ai
pytest -q
