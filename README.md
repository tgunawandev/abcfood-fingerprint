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
fingerprint-ctl backup run tmi            # Full backup to S3
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
| GET | `/attendance/{device}?from=&to=` | Get records |
| GET | `/attendance/{device}/count` | Count records |
| GET | `/users/{device}` | List users |
| POST | `/users/{device}` | Create user |
| PUT | `/users/{device}/{uid}` | Update user |
| DELETE | `/users/{device}/{uid}` | Delete user |
| POST | `/users/{device}/sync` | Sync from Odoo |
| GET | `/fingerprints/{device}/{user_id}` | Get templates |
| GET | `/fingerprints/{device}/count` | Count templates |
| POST | `/backup/{device}` | Trigger backup |
| GET | `/backup/list` | List backups |
| POST | `/backup/restore/{key}` | Restore backup |
| GET | `/health` | Health check |
| GET | `/metrics` | Service metrics |

Interactive docs at `/docs` (Swagger UI).

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

### Tactical RMM Management

```bash
# API endpoint
TRMM_API=https://api-rmm.abcfood.app
TRMM_KEY=0fd23317d10df6b5f39ce9fe6010c588b96fac26e0900793
AGENT_ID=ZFaezOcIfkQqxvJBYPliUhFZoyurDqFdxppvpnDO

# Run command on SASBDOAP001
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" \
  -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"hostname","timeout":30,"run_as_user":false}'

# Check service status
curl -X POST "$TRMM_API/agents/$AGENT_ID/cmd/" \
  -H "X-API-KEY: $TRMM_KEY" \
  -H "Content-Type: application/json" \
  -d '{"shell":"cmd","cmd":"sc query ABCFoodFingerprint","timeout":15,"run_as_user":false}'
```

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
| ZK Protocol | pyzk |
| Config | Pydantic Settings |
| S3 | boto3 (Hetzner) |
| Tunnel | cloudflared |
| Win Service | NSSM |
| Build | Hatchling |
