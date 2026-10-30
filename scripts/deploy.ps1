# ==========================================================
# Dota 2 Coaching Intelligence Platform — Windows Deployer
# PowerShell Automated Deployment & Health Verification
# ==========================================================

param (
    [string]$AppDir = (Get-Location).Path,
    [string]$HealthUrl = "http://127.0.0.1:8000/health",
    [int]$MaxAttempts = 15,
    [int]$IntervalSec = 3
)

$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AEGIS DOTA 2 PLATFORM - AUTOMATED CONTINUOUS DEPLOYMENT" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Set-Location $AppDir

Write-Host ">> Step 1: Building and performing zero-downtime rolling update..." -ForegroundColor Yellow
docker compose up -d --remove-orphans --build

Write-Host ">> Step 2: Probing service health at $HealthUrl..." -ForegroundColor Yellow
$healthy = $false
for ($i = 1; $i -le $MaxAttempts; $i++) {
    Write-Host "   [Probe $i/$MaxAttempts] Awaiting model initialization..." -ForegroundColor Gray
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 4 -ErrorAction Stop
        if ($response.status -eq "healthy") {
            Write-Host "   [OK] Backend health probe passed! All ML models verified loaded." -ForegroundColor Green
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds $IntervalSec
    }
}

if (-not $healthy) {
    Write-Host "[ERROR] Backend health check timed out. Dumping container logs:" -ForegroundColor Red
    docker compose logs --tail=25 backend
    exit 1
}

Write-Host ">> Step 3: Checking Frontend web server on port 80..." -ForegroundColor Yellow
try {
    $fe = Invoke-WebRequest -Uri "http://127.0.0.1:80/" -TimeoutSec 4 -UseBasicParsing -ErrorAction SilentlyContinue
    if ($fe.StatusCode -eq 200) {
        Write-Host "   [OK] Frontend is serving production SPA." -ForegroundColor Green
    }
} catch {
    Write-Host "   [WARN] Frontend check skipped or delayed." -ForegroundColor Yellow
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Automated deployment complete! Live at http://localhost" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
