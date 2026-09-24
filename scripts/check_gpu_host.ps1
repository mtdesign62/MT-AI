$ErrorActionPreference = "Stop"

Write-Host "=== MT AI GPU host preflight ==="

if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    throw "nvidia-smi not found. Install/update the NVIDIA driver first."
}

Write-Host ""
Write-Host "--- NVIDIA ---"
nvidia-smi

Write-Host ""
Write-Host "--- Windows ---"
Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, OSArchitecture

Write-Host ""
Write-Host "--- Memory ---"
$cs = Get-CimInstance Win32_ComputerSystem
$ramGB = [Math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
Write-Host "System RAM: $ramGB GB"

Write-Host ""
Write-Host "--- Disk ---"
Get-PSDrive -PSProvider FileSystem |
    Select-Object Name,
        @{N="FreeGB";E={[Math]::Round($_.Free/1GB,1)}},
        @{N="UsedGB";E={[Math]::Round($_.Used/1GB,1)}}

Write-Host ""
Write-Host "--- Git ---"
if (Get-Command git -ErrorAction SilentlyContinue) {
    git --version
} else {
    Write-Warning "git not found. GitHub Actions checkout requires Git."
}

Write-Host ""
Write-Host "--- Python launcher ---"
if (Get-Command py -ErrorAction SilentlyContinue) {
    py --version
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python --version
} else {
    Write-Host "Python is not installed globally. This is acceptable if actions/setup-python can provision it."
}

Write-Host ""
Write-Host "Preflight complete."
Write-Host "For the GitHub runner use custom labels: gpu,nvidia"
Write-Host "Recommended first MT AI test profile: low-memory, 1024x576, 20 steps."
