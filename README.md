# ABCFood Fingerprint - ZKTeco Middleware Service

ZKTeco X100-C fingerprint machine middleware for ABCFood HRIS integration. Provides REST API + CLI for remote management via Cloudflare tunnel.

## Architecture

```
    Odoo HRIS (odoo-hris.abcfood.app / odoo-hrisos.abcfood.app)
         |
         | HTTPS API calls
         v
    Cloudflared Tunnel (zk-01.abcfood.app)
         |
         v
    PC SASBDOAP001 (Windows Server 2008 R2, 182.10.130.62)
      abcfood-fingerprint (Python 3.8, FastAPI :8000)
      APScheduler (attendance cache + daily backups)
         |
    +----+----+
    |         |
  TMI       Outsourcing
  .168.20   .168.36
  :4370     :4370
```

## Fingerprint Devices

| Name | Key | IP | Port | Serial | Model |
|------|-----|-----|------|--------|-------|
| TMI | `tmi` | 192.168.168.20 | 4370 | 97622 | X100-C |
| Outsourcing | `outsourcing` | 192.168.168.36 | 4370 | 104108 | X100-C |

## Quick Start

### Local Development

```bash
# Install
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your credentials

# Test connections
fingerprint-ctl test-connection

# Start API server
fingerprint-ctl serve
```

### Windows Production (SASBDOAP001)

Deployed via Tactical RMM (`scripts/install-rmm.ps1`):
- Install dir: `C:\abcfood-fingerprint`
- Service: `ABCFoodFingerprint` (NSSM, auto-start)
- Tunnel: `ABCFoodCloudflared` (NSSM, auto-start)
- RMM Agent: `ZFaezOcIfkQqxvJBYPliUhFZoyurDqFdxppvpnDO`
- Git: `C:\Program Files\Git\bin\git.exe` (not in PATH)

```powershell
# Manual install
.\scripts\install-windows.ps1
.\scripts\install-service.ps1

# Remote install via Tactical RMM
# Run scripts/install-rmm.ps1 as script task on agent SASBDOAP001
```

### Docker

```bash
# Development
docker compose up -d
docker compose exec app fingerprint-ctl test-connection

# Production (Dokploy)
docker compose -f docker-compose.prod.yml up -d
```

## Scheduler & Attendance Cache

pyzk must fetch all 100K+ attendance records from the ZK device (protocol limitation), taking ~138s per request. APScheduler runs in-process alongside FastAPI, keeping attendance data cached in memory with 5-minute refresh. API requests hit the cache for instant (<1s) responses.

### Scheduled Jobs

| Job | Trigger | Duration |
|-----|---------|----------|
| Cache refresh TMI | Every 5 min | ~138s |
| Cache refresh Outsourcing | Every 5 min (+1 min stagger) | ~138s |
| Daily backup TMI (with attendance) | 17:00 UTC (00:00 WIB) | ~5s |
| Daily backup Outsourcing | 17:05 UTC | ~5s |
| Cleanup old backups | 18:00 UTC | ~2s |

### Config

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Enable/disable all scheduled jobs |
| `CACHE_REFRESH_MINUTES` | `5` | Attendance cache refresh interval |
| `BACKUP_HOUR_UTC` | `17` | Daily backup hour (17 UTC = 00:00 WIB) |
| `BACKUP_MINUTE_UTC` | `0` | Daily backup minute |
| `BACKUP_RETENTION_DAYS` | `90` | Days to keep old backups |

### Verification

```bash
# Check scheduler is running
curl https://zk-01.abcfood.app/metrics
# -> scheduler_running: true, attendance_cache: {tmi: {cached: true, count: ...}}

# Check cache status for a device
curl -H "X-API-Key: $KEY" https://zk-01.abcfood.app/api/v1/attendance/tmi/cache
# -> {cached: true, fetched_at: "...", count: 103456, is_loading: false}
```

## .env Security

### Protection

The `.env` file contains API keys, S3 credentials, Odoo password, and tunnel token. NTFS ACLs restrict access:

| Path | Permissions | Purpose |
|------|------------|---------|
| `C:\abcfood-fingerprint\` | SYSTEM (Full) + Admins (Full) | No regular Users/Everyone |
| `.env` / `.env.local` | SYSTEM (Read) + Admins (Full) | Service reads, admins edit |
| `logs\` | SYSTEM (Full) + Admins (Full) | Service write access |

NSSM runs the service as `LOCAL SYSTEM`, which retains read access to `.env`. Non-admin RDP users get "Access Denied".

### Apply / Verify

```powershell
# Apply (standalone script)
powershell -ExecutionPolicy Bypass -File C:\abcfood-fingerprint\scripts\secure-env.ps1

# Or via RMM
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"icacls C:\\abcfood-fingerprint /inheritance:r /grant \"NT AUTHORITY\\SYSTEM:(OI)(CI)F\" /grant \"BUILTIN\\Administrators:(OI)(CI)F\" && icacls C:\\abcfood-fingerprint\\.env /inheritance:r /grant \"NT AUTHORITY\\SYSTEM:(R)\" /grant \"BUILTIN\\Administrators:(F)\"","timeout":30,"run_as_user":false}'

# Verify
icacls C:\abcfood-fingerprint\.env
# Expected: BUILTIN\Administrators:(F)  NT AUTHORITY\SYSTEM:(R)

# To edit .env later (admin PowerShell only)
notepad C:\abcfood-fingerprint\.env
```

## CLI Reference

```bash
# Device management
fingerprint-ctl device list              # List devices with status
fingerprint-ctl device info tmi          # Detailed device info
fingerprint-ctl device ping tmi          # Check connectivity
fingerprint-ctl device time tmi          # Get device time
fingerprint-ctl device time tmi --sync   # Sync to system time
fingerprint-ctl device restart tmi --confirm

# Attendance records
fingerprint-ctl attendance get tmi --from 2026-02-17 --to 2026-02-17
fingerprint-ctl attendance count tmi
fingerprint-ctl attendance live tmi      # Live feed (Ctrl+C to stop)
fingerprint-ctl attendance clear tmi --confirm

# User management
fingerprint-ctl user list tmi
fingerprint-ctl user get tmi 123
fingerprint-ctl user add tmi --uid 1 --name "John Doe" --user-id "EMP001" --confirm
fingerprint-ctl user update tmi 1 --name "Jane Doe" --confirm
fingerprint-ctl user delete tmi 1 --confirm
fingerprint-ctl user sync-from-odoo tmi          # Dry run (preview)
fingerprint-ctl user sync-from-odoo tmi --confirm # Apply changes

# Fingerprint templates
fingerprint-ctl finger list tmi
fingerprint-ctl finger count tmi
fingerprint-ctl finger backup tmi                 # Backup to S3
fingerprint-ctl finger restore <s3-key> --confirm

# Backup / Restore
fingerprint-ctl backup run tmi                    # Users + fingerprints
fingerprint-ctl backup run tmi --include-attendance  # Full backup
fingerprint-ctl backup list               # List S3 backups
fingerprint-ctl backup list --device tmi  # Filter by device
fingerprint-ctl backup restore <s3-key> --confirm

# Service
fingerprint-ctl serve                     # Start REST API (:8000)
fingerprint-ctl serve --port 9000         # Custom port
fingerprint-ctl test-connection           # Test all connections
fingerprint-ctl init-check                # Docker init container
fingerprint-ctl status                    # Show configuration
fingerprint-ctl list                      # List all commands
```

## REST API

Base URL: `https://zk-01.abcfood.app/api/v1` (via tunnel) or `http://localhost:8000/api/v1`

Authentication: `X-API-Key` header

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/devices` | List all devices |
| GET | `/devices/{name}` | Device info |
| POST | `/devices/{name}/restart` | Restart device |
| GET | `/devices/{name}/time` | Get device time |
| PUT | `/devices/{name}/time` | Sync device time |
| GET | `/attendance/{device}?from=&to=` | Get records (cache-first) |
| GET | `/attendance/{device}/count` | Count records (cache-first) |
| GET | `/attendance/{device}/cache` | Cache status |
| GET | `/users/{device}` | List users |
| POST | `/users/{device}` | Create user |
| PUT | `/users/{device}/{uid}` | Update user |
| DELETE | `/users/{device}/{uid}` | Delete user |
| POST | `/users/{device}/sync` | Sync from Odoo |
| GET | `/fingerprints/{device}/{user_id}` | Get templates |
| GET | `/fingerprints/{device}/count` | Count templates |
| POST | `/backup/{device}?include_attendance=true` | Trigger backup |
| GET | `/backup/list` | List backups |
| POST | `/backup/restore/{key}` | Restore backup |
| GET | `/health` | Health check |
| GET | `/metrics` | Metrics (scheduler, cache) |

Interactive docs at `/docs` (Swagger UI).

## Deployment via Tactical RMM

### RMM Credentials

```bash
TRMM_API=https://api-rmm.abcfood.app
TRMM_KEY=0fd23317d10df6b5f39ce9fe6010c588b96fac26e0900793
AGENT_ID=ZFaezOcIfkQqxvJBYPliUhFZoyurDqFdxppvpnDO
```

### Update Deployment (git pull + restart)

```bash
# Step 1: Pull latest code
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

# Step 4: Verify
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"sc query ABCFoodFingerprint 2>&1","timeout":15,"run_as_user":false}'

# Step 5: Secure .env
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"icacls C:\\abcfood-fingerprint /inheritance:r /grant \"NT AUTHORITY\\SYSTEM:(OI)(CI)F\" /grant \"BUILTIN\\Administrators:(OI)(CI)F\" && icacls C:\\abcfood-fingerprint\\.env /inheritance:r /grant \"NT AUTHORITY\\SYSTEM:(R)\" /grant \"BUILTIN\\Administrators:(F)\"","timeout":30,"run_as_user":false}'
```

### Initial Setup (no git repo)

If install dir was created from zip (no `.git`), initialize git first:

```bash
# One-time: init git repo
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"cd /d C:\\abcfood-fingerprint && \"C:\\Program Files\\Git\\bin\\git.exe\" init && \"C:\\Program Files\\Git\\bin\\git.exe\" remote add origin https://github.com/tgunawandev/abcfood-fingerprint.git 2>&1","timeout":30,"run_as_user":false}'

# Fetch + checkout
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"cd /d C:\\abcfood-fingerprint && \"C:\\Program Files\\Git\\bin\\git.exe\" fetch origin main && \"C:\\Program Files\\Git\\bin\\git.exe\" checkout -b main origin/main --force 2>&1","timeout":120,"run_as_user":false}'
```

### Utility Commands

```bash
# Run command on SASBDOAP001
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"hostname","timeout":30,"run_as_user":false}'

# Check service status
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"sc query ABCFoodFingerprint","timeout":15,"run_as_user":false}'

# View service logs
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"type C:\\abcfood-fingerprint\\logs\\service.log","timeout":15,"run_as_user":false}'

# Verify .env permissions
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"icacls C:\\abcfood-fingerprint\\.env","timeout":15,"run_as_user":false}'
```

## Infrastructure

### Credentials & Config

| Service | Location |
|---------|----------|
| Production `.env` | `.env.prod` (gitignored) |
| Device config | `config/machines.yml` |
| S3 Bucket | `hz-abcfood-fingerprint` (Hetzner nbg1) |
| Cloudflare Tunnel | `zk-01-abcfood-fingerprint` (d23138fd-3402-4338-947a-7a44f0954029) |
| DNS | `zk-01.abcfood.app` -> tunnel CNAME |
| RMM API Key | `fingerprint-deploy` (svc-claude, expires 2027-02-17) |
| Windows Service | `ABCFoodFingerprint` + `ABCFoodCloudflared` via NSSM |

### Safety Rules

1. **Read-only by default** - write ops require `--confirm` (CLI) or API key (REST)
2. **Device lock** - device disabled during bulk write ops, always re-enabled
3. **Connection lock** - max 1 concurrent connection per device (thread lock)
4. **Timeout** - 60s connection timeout, auto-disconnect
5. **Dry-run** - sync operations default to dry-run mode

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.8 (Win) / 3.11+ (Docker) |
| API | FastAPI + Uvicorn |
| CLI | Typer + Rich |
| Scheduler | APScheduler 3.10 (BackgroundScheduler) |
| ZK Protocol | pyzk |
| Config | Pydantic Settings |
| S3 | boto3 (Hetzner) |
| Tunnel | cloudflared |
| Win Service | NSSM |
| Build | Hatchling |
