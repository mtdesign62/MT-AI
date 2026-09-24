param(
    [Parameter(Mandatory = $true)]
    [string]$Token,

    [string]$RunnerName = "MT-AI-RTX5060Ti",

    [string]$InstallDir = "$env:USERPROFILE\mt-ai-actions-runner",

    [switch]$InstallService
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/mtdesign62/MT-AI"

Write-Host "=== MT AI GitHub GPU Runner Setup ==="
Write-Host "Repository: $RepoUrl"
Write-Host "Runner name: $RunnerName"
Write-Host "Install dir: $InstallDir"
Write-Host ""

if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    throw "nvidia-smi was not found. Install/update the NVIDIA driver before registering this GPU runner."
}

Write-Host "Detected NVIDIA GPU:"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$release = Invoke-RestMethod -Uri "https://api.github.com/repos/actions/runner/releases/latest" -Headers @{ "User-Agent" = "MT-AI-runner-setup" }

$asset = $release.assets | Where-Object { $_.name -match '^actions-runner-win-x64-.*\.zip$' } | Select-Object -First 1

if (-not $asset) {
    throw "Could not find a Windows x64 GitHub Actions runner package in the latest release."
}

$zipPath = Join-Path $env:TEMP $asset.name
Write-Host "Downloading GitHub Actions Runner $($release.tag_name)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath

Write-Host "Extracting runner..."
Get-ChildItem -Path $InstallDir -Force |
    Where-Object { $_.Name -notin @("_work") } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

Push-Location $InstallDir
try {
    Write-Host "Registering runner with labels: gpu,nvidia"
    & .\config.cmd --url $RepoUrl --token $Token --name $RunnerName --labels "gpu,nvidia" --work "_work" --unattended --replace

    if ($LASTEXITCODE -ne 0) {
        throw "GitHub runner registration failed with exit code $LASTEXITCODE."
    }

    if ($InstallService) {
        Write-Host "Installing runner as Windows service..."
        & .\svc.cmd install
        if ($LASTEXITCODE -ne 0) {
            throw "Runner service installation failed. Re-run PowerShell as Administrator."
        }
        & .\svc.cmd start
        if ($LASTEXITCODE -ne 0) {
            throw "Runner service start failed."
        }
        Write-Host ""
        Write-Host "Runner service is installed and started."
        Write-Host "You may close this PowerShell window."
    }
    else {
        Write-Host ""
        Write-Host "Runner registered successfully."
        Write-Host "Starting it in this PowerShell window."
        Write-Host "KEEP THIS WINDOW OPEN while MT AI GPU tests are running."
        Write-Host ""
        & .\run.cmd
    }
}
finally {
    Pop-Location
}
