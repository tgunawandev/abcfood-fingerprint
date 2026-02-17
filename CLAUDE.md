# CLAUDE.md - abcfood-fingerprint

This file provides context and instructions for AI assistants working with this codebase.

## Project Overview

**abcfood-fingerprint** is a Python middleware service for managing ZKTeco X100-C fingerprint machines used in ABCFood employee attendance. It provides both a REST API (FastAPI) and CLI (Typer) for Odoo HRIS integration via cloudflared tunnel.

## Architecture

```
    Odoo HRIS (odoo-hris.abcfood.app)
         |
         | HTTPS API calls
         v
    Cloudflared Tunnel (zk-01.abcfood.app)
         |
         v
    PC SASBDOAP001 (Windows Server 2008 R2)
      abcfood-fingerprint (Python 3.8)
      - FastAPI REST API (:8000)
      - APScheduler (attendance cache + daily backups)
      - CLI (fingerprint-ctl)
      - cloudflared tunnel daemon
         |
    +----+----+
    |         |
  TMI       Outsource
  .168.20   .168.36
  :4370     :4370
```

## Repository Structure

```
abcfood-fingerprint/
+-- src/abcfood_fingerprint/
|   +-- __init__.py
|   +-- __main__.py
|   +-- main.py                    # Typer CLI app entry point
|   +-- config.py                  # Pydantic Settings
|   +-- api/                       # FastAPI REST API
|   |   +-- app.py                 # App factory + lifespan (scheduler)
|   |   +-- deps.py                # Auth, device pool injection
|   |   +-- middleware.py           # Request logging
|   |   +-- routes/
|   |       +-- devices.py
|   |       +-- attendance.py      # Includes /cache status endpoint
|   |       +-- users.py
|   |       +-- fingerprints.py
|   |       +-- backup.py          # Supports include_attendance param
|   +-- cli/                       # Typer CLI subcommands
|   |   +-- device.py
|   |   +-- attendance.py
|   |   +-- user.py
|   |   +-- finger.py
|   |   +-- backup.py              # --include-attendance flag
|   +-- core/                      # Business logic
|   |   +-- device_manager.py
|   |   +-- attendance.py          # Cache-first attendance fetch
|   |   +-- user_sync.py
|   |   +-- fingerprint.py
|   |   +-- backup.py              # Full backup with attendance
|   |   +-- cache.py               # Thread-safe attendance cache
|   |   +-- scheduler.py           # APScheduler jobs
|   +-- zk/                        # ZKTeco abstraction
|   |   +-- client.py              # pyzk wrapper
|   |   +-- models.py              # Pydantic models (BackupRecord has attendance)
|   |   +-- pool.py                # Device pool
|   +-- storage/
|   |   +-- s3.py                  # Hetzner S3
|   +-- utils/
|       +-- notifications.py
|       +-- logging.py
+-- config/
|   +-- machines.yml               # Device registry
+-- scripts/
|   +-- install-windows.ps1        # Windows setup
|   +-- install-service.ps1        # NSSM service registration + .env security
|   +-- install-rmm.ps1            # Remote install via Tactical RMM
|   +-- secure-env.ps1             # Standalone .env permission hardening
|   +-- backup-fingerprints.sh
|   +-- sync-attendance.sh
+-- docker/
|   +-- Dockerfile
|   +-- entrypoint.sh
+-- tests/
+-- docker-compose.yml             # Development
+-- docker-compose.prod.yml        # Production
+-- pyproject.toml
+-- .env.example
+-- CLAUDE.md
```

## Project Standards

| Aspect | Standard |
|--------|----------|
| **CLI Framework** | Typer with Rich |
| **Configuration** | Pydantic BaseSettings |
| **Package Config** | pyproject.toml (hatchling) |
| **Source Layout** | `src/abcfood_fingerprint/` |
| **Python** | 3.8+ (native) / 3.11+ (Docker) |
| **Compatibility** | `from __future__ import annotations` everywhere |
| **API** | FastAPI with API key auth (X-API-Key header) |
| **ZK Protocol** | pyzk with retry, timeout, thread locks |
| **Scheduler** | APScheduler 3.10 BackgroundScheduler |
| **S3** | boto3 with Hetzner endpoint |
| **Testing** | pytest |
| **Docker** | Multi-stage, non-root user |
| **Windows Service** | NSSM |

## Scheduler & Attendance Cache

### Problem
pyzk must fetch all 100K+ attendance records from the ZK device (protocol limitation), taking ~138s per request.

### Solution
APScheduler `BackgroundScheduler` runs in-process alongside FastAPI. Attendance data is cached in memory and refreshed every 5 minutes. API requests hit the cache for instant responses.

### Scheduler Jobs

| Job | Trigger | Duration |
|-----|---------|----------|
| Cache refresh TMI | Every 5 min | ~138s |
| Cache refresh Outsourcing | Every 5 min (+1 min stagger) | ~138s |
| Daily backup TMI | 17:00 UTC (00:00 WIB) | ~5s (cache hit) |
| Daily backup Outsourcing | 17:05 UTC | ~5s (cache hit) |
| Cleanup old backups | 18:00 UTC | ~2s |

### Config Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Enable/disable all scheduled jobs |
| `CACHE_REFRESH_MINUTES` | `5` | Attendance cache refresh interval |
| `BACKUP_HOUR_UTC` | `17` | Daily backup hour (17 UTC = 00:00 WIB) |
| `BACKUP_MINUTE_UTC` | `0` | Daily backup minute |
| `BACKUP_RETENTION_DAYS` | `90` | Days to keep old backups |

### Key Modules

- **`core/cache.py`** — `AttendanceCache` singleton with thread-safe `refresh()`, `get()`, `get_records_raw()`, `get_count()`, `get_status()`
- **`core/scheduler.py`** — Job definitions + `start_scheduler()` / `stop_scheduler()` lifecycle
- **`api/app.py`** — `lifespan` context manager starts scheduler on startup, stops on shutdown

## Deployment

### Windows (Production - PC SASBDOAP001)
- Native Python 3.8 (max for Win Server 2008 R2)
- NSSM for service management
- cloudflared for tunnel
- Git installed at `C:\Program Files\Git\bin\git.exe` (not in PATH)
- Install: `scripts/install-windows.ps1` then `scripts/install-service.ps1`
- Remote install via RMM: `scripts/install-rmm.ps1`

### Deployment via Tactical RMM API

```bash
TRMM_API=https://api-rmm.abcfood.app
TRMM_KEY=0fd23317d10df6b5f39ce9fe6010c588b96fac26e0900793
AGENT_ID=ZFaezOcIfkQqxvJBYPliUhFZoyurDqFdxppvpnDO

# Step 1: Pull latest code (git is at C:\Program Files\Git\bin\git.exe)
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"cd /d C:\\abcfood-fingerprint && \"C:\\Program Files\\Git\\bin\\git.exe\" pull origin main 2>&1","timeout":120,"run_as_user":false}'

# Step 2: Install/update dependencies
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"C:\\abcfood-fingerprint\\venv\\Scripts\\pip.exe install -e C:\\abcfood-fingerprint 2>&1","timeout":300,"run_as_user":false}'

# Step 3: Restart service
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"C:\\abcfood-fingerprint\\nssm\\nssm.exe restart ABCFoodFingerprint 2>&1","timeout":30,"run_as_user":false}'

# Step 4: Secure .env (after any .env changes)
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"icacls C:\\abcfood-fingerprint /inheritance:r /grant \"NT AUTHORITY\\SYSTEM:(OI)(CI)F\" /grant \"BUILTIN\\Administrators:(OI)(CI)F\" 2>&1 && icacls C:\\abcfood-fingerprint\\.env /inheritance:r /grant \"NT AUTHORITY\\SYSTEM:(R)\" /grant \"BUILTIN\\Administrators:(F)\" 2>&1","timeout":30,"run_as_user":false}'

# Step 5: Verify
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"sc query ABCFoodFingerprint 2>&1","timeout":15,"run_as_user":false}'
```

### Initial Setup (no git repo)
If the install dir was created from a zip (no `.git`), initialize git first:
```bash
# One-time: init git repo
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"cd /d C:\\abcfood-fingerprint && \"C:\\Program Files\\Git\\bin\\git.exe\" init && \"C:\\Program Files\\Git\\bin\\git.exe\" remote add origin https://github.com/tgunawandev/abcfood-fingerprint.git 2>&1","timeout":30,"run_as_user":false}'

# Then fetch + checkout
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"cd /d C:\\abcfood-fingerprint && \"C:\\Program Files\\Git\\bin\\git.exe\" fetch origin main && \"C:\\Program Files\\Git\\bin\\git.exe\" checkout -b main origin/main --force 2>&1","timeout":120,"run_as_user":false}'
```

### Docker (Dev/Dokploy)
- ENTRYPOINT is `["fingerprint-ctl"]`, compose commands use `["serve"]`
- `network_mode: host` for LAN access to fingerprint devices
- Init container validates connections before app starts

## .env Security

### Threat Model
The `.env` file contains API keys, S3 credentials, Odoo password, and tunnel token. Non-admin users who RDP to the server should not be able to read these secrets.

### Protection Applied
NTFS ACLs lock down the install directory and `.env` file:

| Path | Permissions | Purpose |
|------|------------|---------|
| `C:\abcfood-fingerprint\` | SYSTEM (Full) + Administrators (Full) | No regular Users/Everyone access |
| `.env` / `.env.local` | SYSTEM (Read) + Administrators (Full) | Service can read, admins can edit |
| `logs\` | SYSTEM (Full) + Administrators (Full) | Service needs write for logs |

### How It Works
- NSSM runs the `ABCFoodFingerprint` service as `LOCAL SYSTEM` by default
- `SYSTEM` retains read access to `.env`, so pydantic-settings loads normally
- Regular user accounts (non-admin RDP) get "Access Denied" on `.env`

### Scripts
- **`scripts/secure-env.ps1`** — Standalone hardening script (run anytime)
- **`scripts/install-service.ps1`** — Includes security step automatically
- **`scripts/install-rmm.ps1`** — Includes security step automatically

### To Edit .env Later
Use an admin PowerShell: `notepad C:\abcfood-fingerprint\.env`

### Verify Permissions
```powershell
icacls C:\abcfood-fingerprint\.env
# Expected output:
#   BUILTIN\Administrators:(F)
#   NT AUTHORITY\SYSTEM:(R)
```

## CLI Commands

```bash
# Device management
fingerprint-ctl device list
fingerprint-ctl device info tmi
fingerprint-ctl device ping tmi
fingerprint-ctl device time tmi --sync
fingerprint-ctl device restart tmi --confirm

# Attendance
fingerprint-ctl attendance get tmi --from 2026-02-17
fingerprint-ctl attendance count tmi
fingerprint-ctl attendance live tmi
fingerprint-ctl attendance clear tmi --confirm

# Users
fingerprint-ctl user list tmi
fingerprint-ctl user get tmi 123
fingerprint-ctl user add tmi --uid 1 --name "John" --user-id "123" --confirm
fingerprint-ctl user sync-from-odoo tmi --confirm

# Fingerprints
fingerprint-ctl finger list tmi
fingerprint-ctl finger count tmi
fingerprint-ctl finger backup tmi
fingerprint-ctl finger restore <s3-key> --confirm

# Backup (with optional attendance)
fingerprint-ctl backup run tmi
fingerprint-ctl backup run tmi --include-attendance
fingerprint-ctl backup list
fingerprint-ctl backup restore <s3-key> --confirm

# Service
fingerprint-ctl serve
fingerprint-ctl test-connection
fingerprint-ctl init-check
fingerprint-ctl status
fingerprint-ctl list
```

## Safety Rules

1. **Read-only by default** - write ops require `--confirm` (CLI) or API key (REST)
2. **Device lock** - disable device during bulk ops, always re-enable
3. **Auto-backup** - backup before destructive operations
4. **Connection lock** - max 1 concurrent connection per device (thread lock)
5. **Timeout** - 60s connection timeout, auto-disconnect
6. **Dry-run** - `--dry-run` flag for sync operations (default: true)

## Environment Variables

See `.env.example` for all variables. Key ones:
- `ZK_MACHINES_CONFIG` - Path to machines.yml
- `API_KEY` - API authentication key
- `S3_*` - Hetzner S3 credentials
- `ODOO_*` - Odoo HRIS connection
- `CLOUDFLARE_TUNNEL_TOKEN` - Cloudflared tunnel token
- `SCHEDULER_ENABLED` - Enable APScheduler (default: true)
- `CACHE_REFRESH_MINUTES` - Cache refresh interval (default: 5)
- `BACKUP_HOUR_UTC` / `BACKUP_MINUTE_UTC` - Daily backup time (default: 17:00 UTC)

## Fingerprint Devices

| Name | Key | IP | Serial |
|------|-----|-----|--------|
| TMI | tmi | 192.168.168.20:4370 | 97622 |
| Outsourcing | outsourcing | 192.168.168.36:4370 | 104108 |
