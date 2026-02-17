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
|   |   +-- app.py                 # App factory
|   |   +-- deps.py                # Auth, device pool injection
|   |   +-- middleware.py           # Request logging
|   |   +-- routes/
|   |       +-- devices.py
|   |       +-- attendance.py
|   |       +-- users.py
|   |       +-- fingerprints.py
|   |       +-- backup.py
|   +-- cli/                       # Typer CLI subcommands
|   |   +-- device.py
|   |   +-- attendance.py
|   |   +-- user.py
|   |   +-- finger.py
|   |   +-- backup.py
|   +-- core/                      # Business logic
|   |   +-- device_manager.py
|   |   +-- attendance.py
|   |   +-- user_sync.py
|   |   +-- fingerprint.py
|   |   +-- backup.py
|   +-- zk/                        # ZKTeco abstraction
|   |   +-- client.py              # pyzk wrapper
|   |   +-- models.py              # Pydantic models
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
|   +-- install-service.ps1        # NSSM service registration
|   +-- install-rmm.ps1            # Remote install via Tactical RMM
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
| **S3** | boto3 with Hetzner endpoint |
| **Testing** | pytest |
| **Docker** | Multi-stage, non-root user |
| **Windows Service** | NSSM |

## Deployment

### Windows (Production - PC SASBDOAP001)
- Native Python 3.8 (max for Win Server 2008 R2)
- NSSM for service management
- cloudflared for tunnel
- Install: `scripts/install-windows.ps1` then `scripts/install-service.ps1`
- Remote install via RMM: `scripts/install-rmm.ps1`

### Docker (Dev/Dokploy)
- ENTRYPOINT is `["fingerprint-ctl"]`, compose commands use `["serve"]`
- `network_mode: host` for LAN access to fingerprint devices
- Init container validates connections before app starts

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

# Backup
fingerprint-ctl backup run tmi
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

## Fingerprint Devices

| Name | Key | IP | Serial |
|------|-----|-----|--------|
| TMI | tmi | 192.168.168.20:4370 | 97622 |
| Outsourcing | outsourcing | 192.168.168.36:4370 | 104108 |
