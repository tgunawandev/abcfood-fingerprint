# install-service.ps1 - Register fingerprint-ctl and cloudflared as Windows services via NSSM
# Run as Administrator

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "C:\abcfood-fingerprint"
$NSSM = "$INSTALL_DIR\nssm\nssm.exe"
$VENV_PYTHON = "$INSTALL_DIR\venv\Scripts\python.exe"
$SERVICE_NAME = "ABCFoodFingerprint"
$CLOUDFLARED_SERVICE = "ABCFoodCloudflared"

Write-Host "=== Registering Windows Services ===" -ForegroundColor Cyan

# Load tunnel token from .env
$envFile = "$INSTALL_DIR\.env"
$tunnelToken = ""
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^CLOUDFLARE_TUNNEL_TOKEN=(.+)$") {
            $tunnelToken = $Matches[1]
        }
    }
}

# --- Fingerprint API Service ---
Write-Host "`n[1/2] Registering $SERVICE_NAME service..." -ForegroundColor Yellow

# Remove existing service if present
& $NSSM stop $SERVICE_NAME 2>$null
& $NSSM remove $SERVICE_NAME confirm 2>$null

& $NSSM install $SERVICE_NAME $VENV_PYTHON "-m" "abcfood_fingerprint" "serve"
& $NSSM set $SERVICE_NAME AppDirectory $INSTALL_DIR
& $NSSM set $SERVICE_NAME Description "ABCFood ZKTeco Fingerprint Middleware API"
& $NSSM set $SERVICE_NAME Start SERVICE_AUTO_START
& $NSSM set $SERVICE_NAME AppStdout "$INSTALL_DIR\logs\service.log"
& $NSSM set $SERVICE_NAME AppStderr "$INSTALL_DIR\logs\service-error.log"
& $NSSM set $SERVICE_NAME AppRotateFiles 1
& $NSSM set $SERVICE_NAME AppRotateBytes 10485760

# Create logs directory
New-Item -ItemType Directory -Path "$INSTALL_DIR\logs" -Force | Out-Null

Write-Host "  $SERVICE_NAME service registered" -ForegroundColor Green

# --- Cloudflared Tunnel Service ---
if ($tunnelToken) {
    Write-Host "`n[2/2] Registering $CLOUDFLARED_SERVICE service..." -ForegroundColor Yellow

    & $NSSM stop $CLOUDFLARED_SERVICE 2>$null
    & $NSSM remove $CLOUDFLARED_SERVICE confirm 2>$null

    & $NSSM install $CLOUDFLARED_SERVICE "$INSTALL_DIR\cloudflared.exe" "tunnel" "run" "--token" $tunnelToken
    & $NSSM set $CLOUDFLARED_SERVICE AppDirectory $INSTALL_DIR
    & $NSSM set $CLOUDFLARED_SERVICE Description "Cloudflare Tunnel for ABCFood Fingerprint"
    & $NSSM set $CLOUDFLARED_SERVICE Start SERVICE_AUTO_START
    & $NSSM set $CLOUDFLARED_SERVICE AppStdout "$INSTALL_DIR\logs\cloudflared.log"
    & $NSSM set $CLOUDFLARED_SERVICE AppStderr "$INSTALL_DIR\logs\cloudflared-error.log"
    & $NSSM set $CLOUDFLARED_SERVICE AppRotateFiles 1
    & $NSSM set $CLOUDFLARED_SERVICE AppRotateBytes 10485760

    Write-Host "  $CLOUDFLARED_SERVICE service registered" -ForegroundColor Green
} else {
    Write-Host "`n[2/2] Skipping cloudflared (no CLOUDFLARE_TUNNEL_TOKEN in .env)" -ForegroundColor Yellow
}

# --- Start Services ---
Write-Host "`nStarting services..." -ForegroundColor Yellow
& $NSSM start $SERVICE_NAME
Write-Host "  $SERVICE_NAME started" -ForegroundColor Green

if ($tunnelToken) {
    & $NSSM start $CLOUDFLARED_SERVICE
    Write-Host "  $CLOUDFLARED_SERVICE started" -ForegroundColor Green
}

Write-Host "`n=== Services Registered ===" -ForegroundColor Cyan
Write-Host "Check status: $NSSM status $SERVICE_NAME"
Write-Host "View logs: Get-Content $INSTALL_DIR\logs\service.log -Tail 50"
