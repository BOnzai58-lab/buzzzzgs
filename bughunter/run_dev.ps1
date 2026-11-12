# BugHunter AI — Local Development Launcher
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       Starting BugHunter AI Platform    " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Start Backend in new window
Write-Host "[1/2] Starting Backend API (http://localhost:8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; .venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"

# 2. Start Frontend in new window
Write-Host "[2/2] Starting Frontend UI (http://localhost:3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm run dev"

Write-Host "`nBugHunter AI is launching!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
