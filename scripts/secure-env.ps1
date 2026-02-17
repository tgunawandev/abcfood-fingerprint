# secure-env.ps1 - Lock down .env and install directory permissions
# Run as Administrator on PC SASBDOAP001
#
# What this does:
#   1. Removes inherited permissions from the install directory
#   2. Grants only SYSTEM (service) and Administrators access to the folder
#   3. Extra-restricts .env so only SYSTEM can read it (not regular users)
#   4. Verifies the service can still access everything
#
# The NSSM service runs as LOCAL SYSTEM, so SYSTEM must have read access.

$ErrorActionPreference = "Stop"

$INSTALL_DIR = "C:\abcfood-fingerprint"
$ENV_FILE = "$INSTALL_DIR\.env"
$ENV_LOCAL = "$INSTALL_DIR\.env.local"
$SERVICE_NAME = "ABCFoodFingerprint"

Write-Host "=== Securing ABCFood Fingerprint ===" -ForegroundColor Cyan

# Check running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run this script as Administrator" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $INSTALL_DIR)) {
    Write-Host "ERROR: Install directory not found: $INSTALL_DIR" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------
# Step 1: Secure the install directory
# -----------------------------------------------------------------------
Write-Host "`n[1/4] Securing install directory..." -ForegroundColor Yellow

# Remove inherited permissions, grant SYSTEM + Administrators full control
icacls $INSTALL_DIR /inheritance:r /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /grant "BUILTIN\Administrators:(OI)(CI)F"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to set folder permissions" -ForegroundColor Red
    exit 1
}
Write-Host "  Folder locked: SYSTEM + Administrators only" -ForegroundColor Green

# -----------------------------------------------------------------------
# Step 2: Extra-restrict .env files (read-only for SYSTEM)
# -----------------------------------------------------------------------
Write-Host "`n[2/4] Restricting .env files..." -ForegroundColor Yellow

foreach ($envPath in @($ENV_FILE, $ENV_LOCAL)) {
    if (Test-Path $envPath) {
        # Remove inherited permissions, SYSTEM=Read, Administrators=Full
        icacls $envPath /inheritance:r /grant "NT AUTHORITY\SYSTEM:(R)" /grant "BUILTIN\Administrators:(F)"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Secured: $envPath" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Failed to secure $envPath" -ForegroundColor Yellow
        }
    }
}

# -----------------------------------------------------------------------
# Step 3: Secure logs directory (SYSTEM can write, Admins full)
# -----------------------------------------------------------------------
Write-Host "`n[3/4] Securing logs directory..." -ForegroundColor Yellow

$logsDir = "$INSTALL_DIR\logs"
if (Test-Path $logsDir) {
    icacls $logsDir /inheritance:r /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /grant "BUILTIN\Administrators:(OI)(CI)F"
    Write-Host "  Logs directory secured" -ForegroundColor Green
}

# -----------------------------------------------------------------------
# Step 4: Verify service can start
# -----------------------------------------------------------------------
Write-Host "`n[4/4] Verifying service..." -ForegroundColor Yellow

$svcStatus = (Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue)
if ($svcStatus) {
    if ($svcStatus.Status -eq "Running") {
        Write-Host "  Service is running (OK)" -ForegroundColor Green
    } else {
        Write-Host "  Service is $($svcStatus.Status), attempting start..." -ForegroundColor Yellow
        Start-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        $svcStatus = Get-Service -Name $SERVICE_NAME
        if ($svcStatus.Status -eq "Running") {
            Write-Host "  Service started successfully" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Service status is $($svcStatus.Status)" -ForegroundColor Yellow
            Write-Host "  Check logs: Get-Content $INSTALL_DIR\logs\service.log -Tail 20" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  Service not found (run install-service.ps1 first)" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
Write-Host "`n=== Security Applied ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Permissions:"
Write-Host "  $INSTALL_DIR       -> SYSTEM(Full) + Admins(Full)"
Write-Host "  .env / .env.local  -> SYSTEM(Read) + Admins(Full)"
Write-Host "  logs/              -> SYSTEM(Full) + Admins(Full)"
Write-Host ""
Write-Host "To verify:" -ForegroundColor Yellow
Write-Host "  icacls $ENV_FILE"
Write-Host "  icacls $INSTALL_DIR"
Write-Host ""
Write-Host "To edit .env later, use an admin PowerShell:"
Write-Host "  notepad $ENV_FILE"
