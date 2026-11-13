# ==============================================================================
# BugHunter AI — Windows Runtime Launcher
# ==============================================================================
$ErrorActionPreference = "Continue"

$DIR = Split-Path -Parent $PSScriptRoot
Set-Location $DIR

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "           BugHunter AI — Starting on Windows                   " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Ensure backend/.env exists
if (-not (Test-Path "backend\.env")) {
    if (Test-Path ".env") {
        Write-Host "[*] Copying root .env to backend\.env..." -ForegroundColor Yellow
        Copy-Item ".env" "backend\.env"
    } elseif (Test-Path "backend\.env.example") {
        Write-Host "[*] Creating backend\.env from example..." -ForegroundColor Yellow
        Copy-Item "backend\.env.example" "backend\.env"
    }
}

$env:SECRET_KEY = if ($env:SECRET_KEY) { $env:SECRET_KEY } else { "b9f2d1e8c7a6b5e4d3c2b1a0f9e8d7c6b5a4938271605f4e3d2c1b0a9f8e7d6c" }
$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "sqlite+aiosqlite:///./bughunter.db" }
$env:SYNC_DATABASE_URL = if ($env:SYNC_DATABASE_URL) { $env:SYNC_DATABASE_URL } else { "sqlite:///./bughunter.db" }

# Start Backend
Write-Host "[*] Launching Backend API on 127.0.0.1:8000..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "backend\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory "$DIR\backend" -PassThru

# Start Frontend
Write-Host "[*] Launching Frontend UI on http://localhost:3000..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --port 3000" -WorkingDirectory "$DIR\frontend" -PassThru

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " [+] BugHunter AI is RUNNING!" -ForegroundColor Green
Write-Host "   Dashboard : http://localhost:3000" -ForegroundColor White
Write-Host "   API Docs  : http://localhost:8000/docs" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop services.`n"

try {
    while ($true) {
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    if ($backendProcess -and -not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id -Force }
    if ($frontendProcess -and -not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id -Force }
}

