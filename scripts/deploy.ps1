# ==========================================================
# Dota 2 Coaching Intelligence Platform — Windows Deployer
# PowerShell Automated Deployment & Health Verification
# ==========================================================

param (
    [string]$AppDir = (Get-Location).Path,
    [string]$HealthUrl = "http://127.0.0.1:8000/health",
    [int]$MaxAttempts = 15,
    [int]$IntervalSec = 5
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AEGIS DOTA 2 PLATFORM — AUTOMATED WINDOWS DEPLOYER" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Set-Location $AppDir

Write-Host ">> Step 1: Pulling latest changes from repository..." -ForegroundColor Yellow
try {
    git fetch origin
    git pull origin master
} catch {
    Write-Host "Notice: Git pull skipped or on different branch." -ForegroundColor Gray
}

Write-Host ">> Step 2: Building and restarting containers..." -ForegroundColor Yellow
docker compose up -d --remove-orphans --build

Write-Host ">> Step 3: Verifying service health at $HealthUrl..." -ForegroundColor Yellow
$healthy = $false
for ($i = 1; $i -le $MaxAttempts; $i++) {
    Write-Host "   [Probe $i/$MaxAttempts] Checking backend..." -ForegroundColor Gray
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5 -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "   [OK] Backend health probe passed! Model loaded successfully." -ForegroundColor Green
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds $IntervalSec
    }
}

if (-not $healthy) {
    Write-Host "[ERROR] Backend failed health check! Check docker logs:" -ForegroundColor Red
    docker compose logs --tail=30 backend
    exit 1
}

Write-Host ">> Step 4: Pruning unused images..." -ForegroundColor Yellow
docker image prune -f

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Automated deployment complete!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green

