# install-rmm.ps1 - Remote install via Tactical RMM
# Deploy this as a script task in Tactical RMM on agent SASBDOAP001
# Tactical RMM Agent ID: ZFaezOcIfkQqxvJBYPliUhFZoyurDqFdxppvpnDO
#
# Usage in Tactical RMM:
#   1. Go to Scripts > Add Script > PowerShell
#   2. Paste this script
#   3. Run on agent: SASBDOAP001
#   4. Set timeout: 600 seconds (10 min)
#
# Environment variables to set in RMM (Script Arguments or Custom Fields):
#   CLOUDFLARE_TUNNEL_TOKEN, API_KEY, S3_ACCESS_KEY, S3_SECRET_KEY,
#   ODOO_PASSWORD

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "C:\abcfood-fingerprint"
$REPO_URL = "https://github.com/tgunawandev/abcfood-fingerprint.git"
$PYTHON_VERSION = "3.8.20"
$PYTHON_URL = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-amd64.exe"
$NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"
$CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

Write-Host "=== ABCFood Fingerprint - RMM Remote Install ===" -ForegroundColor Cyan
Write-Host "Target: $env:COMPUTERNAME"
Write-Host "Install Dir: $INSTALL_DIR"

# -----------------------------------------------------------------------
# Step 1: Install Python 3.8 if not present
# -----------------------------------------------------------------------
Write-Host "`n[1/7] Checking Python..." -ForegroundColor Yellow
if (-not (Test-Path "C:\Python38\python.exe")) {
    Write-Host "  Downloading Python $PYTHON_VERSION..."
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    (New-Object System.Net.WebClient).DownloadFile($PYTHON_URL, $pythonInstaller)
    Write-Host "  Installing Python (silent)..."
    Start-Process -Wait -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "TargetDir=C:\Python38", "PrependPath=1"
    Remove-Item $pythonInstaller -Force -ErrorAction SilentlyContinue
    Write-Host "  Python $PYTHON_VERSION installed" -ForegroundColor Green
} else {
    Write-Host "  Python already installed" -ForegroundColor Green
}

# -----------------------------------------------------------------------
# Step 2: Create install directory
# -----------------------------------------------------------------------
Write-Host "`n[2/7] Setting up directory..." -ForegroundColor Yellow
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}
New-Item -ItemType Directory -Path "$INSTALL_DIR\logs" -Force | Out-Null

# -----------------------------------------------------------------------
# Step 3: Clone or update repository
# -----------------------------------------------------------------------
Write-Host "`n[3/7] Getting source code..." -ForegroundColor Yellow
if (Get-Command git -ErrorAction SilentlyContinue) {
    if (Test-Path "$INSTALL_DIR\.git") {
        Set-Location $INSTALL_DIR
        git pull origin main
        Write-Host "  Repository updated" -ForegroundColor Green
    } else {
        git clone $REPO_URL $INSTALL_DIR
        Write-Host "  Repository cloned" -ForegroundColor Green
    }
} else {
    # Fallback: download as zip if git is not available
    Write-Host "  Git not found, downloading zip..."
    $zipUrl = "$REPO_URL/archive/refs/heads/main.zip"
    $zipPath = "$env:TEMP\abcfood-fingerprint.zip"
    (New-Object System.Net.WebClient).DownloadFile($zipUrl, $zipPath)
    Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\abcfood-fingerprint-extract" -Force
    Copy-Item "$env:TEMP\abcfood-fingerprint-extract\abcfood-fingerprint-main\*" $INSTALL_DIR -Recurse -Force
    Remove-Item $zipPath, "$env:TEMP\abcfood-fingerprint-extract" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Source extracted" -ForegroundColor Green
}

Set-Location $INSTALL_DIR

# -----------------------------------------------------------------------
# Step 4: Install NSSM
# -----------------------------------------------------------------------
Write-Host "`n[4/7] Installing NSSM..." -ForegroundColor Yellow
if (-not (Test-Path "$INSTALL_DIR\nssm\nssm.exe")) {
    $nssmZip = "$env:TEMP\nssm.zip"
    (New-Object System.Net.WebClient).DownloadFile($NSSM_URL, $nssmZip)
    Expand-Archive -Path $nssmZip -DestinationPath "$env:TEMP\nssm-extract" -Force
    New-Item -ItemType Directory -Path "$INSTALL_DIR\nssm" -Force | Out-Null
    Copy-Item "$env:TEMP\nssm-extract\nssm-2.24\win64\nssm.exe" "$INSTALL_DIR\nssm\nssm.exe"
    Remove-Item $nssmZip, "$env:TEMP\nssm-extract" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  NSSM installed" -ForegroundColor Green
} else {
    Write-Host "  NSSM already present" -ForegroundColor Green
}

# -----------------------------------------------------------------------
# Step 5: Install cloudflared
# -----------------------------------------------------------------------
Write-Host "`n[5/7] Installing cloudflared..." -ForegroundColor Yellow
if (-not (Test-Path "$INSTALL_DIR\cloudflared.exe")) {
    (New-Object System.Net.WebClient).DownloadFile($CLOUDFLARED_URL, "$INSTALL_DIR\cloudflared.exe")
    Write-Host "  cloudflared installed" -ForegroundColor Green
} else {
    Write-Host "  cloudflared already present" -ForegroundColor Green
}

# -----------------------------------------------------------------------
# Step 6: Create venv and install package
# -----------------------------------------------------------------------
Write-Host "`n[6/7] Setting up Python environment..." -ForegroundColor Yellow
if (-not (Test-Path "$INSTALL_DIR\venv\Scripts\python.exe")) {
    & C:\Python38\python.exe -m venv "$INSTALL_DIR\venv"
}
& "$INSTALL_DIR\venv\Scripts\pip.exe" install --upgrade pip 2>&1 | Out-Null
& "$INSTALL_DIR\venv\Scripts\pip.exe" install -e "$INSTALL_DIR" 2>&1
Write-Host "  Package installed" -ForegroundColor Green

# -----------------------------------------------------------------------
# Step 7: Create .env if not present, register services
# -----------------------------------------------------------------------
Write-Host "`n[7/7] Configuring services..." -ForegroundColor Yellow
if (-not (Test-Path "$INSTALL_DIR\.env")) {
    Copy-Item "$INSTALL_DIR\.env.example" "$INSTALL_DIR\.env"
    Write-Host "  Created .env from template (CONFIGURE BEFORE STARTING!)" -ForegroundColor Yellow
}

# Register services via NSSM
$NSSM_EXE = "$INSTALL_DIR\nssm\nssm.exe"
$VENV_PYTHON = "$INSTALL_DIR\venv\Scripts\python.exe"

# Stop existing services
& $NSSM_EXE stop ABCFoodFingerprint 2>$null
& $NSSM_EXE remove ABCFoodFingerprint confirm 2>$null

& $NSSM_EXE install ABCFoodFingerprint $VENV_PYTHON "-m" "abcfood_fingerprint" "serve"
& $NSSM_EXE set ABCFoodFingerprint AppDirectory $INSTALL_DIR
& $NSSM_EXE set ABCFoodFingerprint Description "ABCFood ZKTeco Fingerprint Middleware API"
& $NSSM_EXE set ABCFoodFingerprint Start SERVICE_AUTO_START
& $NSSM_EXE set ABCFoodFingerprint AppStdout "$INSTALL_DIR\logs\service.log"
& $NSSM_EXE set ABCFoodFingerprint AppStderr "$INSTALL_DIR\logs\service-error.log"
& $NSSM_EXE set ABCFoodFingerprint AppRotateFiles 1
& $NSSM_EXE set ABCFoodFingerprint AppRotateBytes 10485760

Write-Host "  ABCFoodFingerprint service registered" -ForegroundColor Green

# Start service
& $NSSM_EXE start ABCFoodFingerprint
Write-Host "  ABCFoodFingerprint service started" -ForegroundColor Green

# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
Write-Host "`n=== RMM Install Complete ===" -ForegroundColor Cyan
Write-Host "Install dir: $INSTALL_DIR"
Write-Host "Service: ABCFoodFingerprint (auto-start)"
Write-Host ""
Write-Host "IMPORTANT: Edit $INSTALL_DIR\.env with production credentials"
Write-Host "Then restart: $NSSM_EXE restart ABCFoodFingerprint"
Write-Host ""
Write-Host "Test: & $INSTALL_DIR\venv\Scripts\python.exe -m abcfood_fingerprint test-connection"
