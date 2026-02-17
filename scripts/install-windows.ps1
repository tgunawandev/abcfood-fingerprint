# install-windows.ps1 - Setup Python, NSSM, cloudflared on Windows Server 2008 R2
# Run as Administrator

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "C:\abcfood-fingerprint"
$PYTHON_VERSION = "3.8.20"
$PYTHON_URL = "https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-amd64.exe"
$NSSM_URL = "https://nssm.cc/release/nssm-2.24.zip"
$CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

Write-Host "=== ABCFood Fingerprint - Windows Setup ===" -ForegroundColor Cyan

# Create install directory
if (-not (Test-Path $INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
}
Set-Location $INSTALL_DIR

# --- Python 3.8 ---
Write-Host "`n[1/5] Installing Python $PYTHON_VERSION..." -ForegroundColor Yellow
$pythonInstaller = "$INSTALL_DIR\python-installer.exe"
if (-not (Test-Path "C:\Python38\python.exe")) {
    Invoke-WebRequest -Uri $PYTHON_URL -OutFile $pythonInstaller
    Start-Process -Wait -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "TargetDir=C:\Python38", "PrependPath=1"
    Remove-Item $pythonInstaller -Force
    Write-Host "  Python installed to C:\Python38" -ForegroundColor Green
} else {
    Write-Host "  Python already installed" -ForegroundColor Green
}

# --- NSSM ---
Write-Host "`n[2/5] Installing NSSM..." -ForegroundColor Yellow
$nssmZip = "$INSTALL_DIR\nssm.zip"
if (-not (Test-Path "$INSTALL_DIR\nssm\nssm.exe")) {
    Invoke-WebRequest -Uri $NSSM_URL -OutFile $nssmZip
    Expand-Archive -Path $nssmZip -DestinationPath "$INSTALL_DIR\nssm-extract" -Force
    New-Item -ItemType Directory -Path "$INSTALL_DIR\nssm" -Force | Out-Null
    Copy-Item "$INSTALL_DIR\nssm-extract\nssm-2.24\win64\nssm.exe" "$INSTALL_DIR\nssm\nssm.exe"
    Remove-Item $nssmZip, "$INSTALL_DIR\nssm-extract" -Recurse -Force
    Write-Host "  NSSM installed" -ForegroundColor Green
} else {
    Write-Host "  NSSM already installed" -ForegroundColor Green
}

# --- cloudflared ---
Write-Host "`n[3/5] Installing cloudflared..." -ForegroundColor Yellow
if (-not (Test-Path "$INSTALL_DIR\cloudflared.exe")) {
    Invoke-WebRequest -Uri $CLOUDFLARED_URL -OutFile "$INSTALL_DIR\cloudflared.exe"
    Write-Host "  cloudflared installed" -ForegroundColor Green
} else {
    Write-Host "  cloudflared already installed" -ForegroundColor Green
}

# --- Virtual Environment ---
Write-Host "`n[4/5] Creating virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "$INSTALL_DIR\venv\Scripts\python.exe")) {
    C:\Python38\python.exe -m venv "$INSTALL_DIR\venv"
    Write-Host "  Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists" -ForegroundColor Green
}

# --- Install Package ---
Write-Host "`n[5/5] Installing abcfood-fingerprint..." -ForegroundColor Yellow
& "$INSTALL_DIR\venv\Scripts\pip.exe" install --upgrade pip
& "$INSTALL_DIR\venv\Scripts\pip.exe" install -e .
Write-Host "  Package installed" -ForegroundColor Green

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Copy .env.example to .env and configure"
Write-Host "  2. Run: .\scripts\install-service.ps1"
Write-Host "  3. Configure cloudflared tunnel token in .env"
