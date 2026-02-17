"""Main CLI application entry point."""
from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.table import Table
import rich.box

from abcfood_fingerprint.cli import attendance, backup, device, finger, user
from abcfood_fingerprint.config import get_settings
from abcfood_fingerprint.utils.logging import setup_logging

# Initialize Typer app
app = typer.Typer(
    name="fingerprint-ctl",
    help="ABCFood ZKTeco Fingerprint Middleware",
    add_completion=False,
)

console = Console()

# Include sub-apps
app.add_typer(device.app)
app.add_typer(attendance.app)
app.add_typer(user.app)
app.add_typer(finger.app)
app.add_typer(backup.app)


@app.callback()
def main_callback(
    log_level: str = typer.Option("INFO", "--log-level", help="Log level"),
):
    """ABCFood ZKTeco Fingerprint Middleware CLI."""
    setup_logging(log_level)


# ---------------------------------------------------------------------------
# Serve command (FastAPI + health)
# ---------------------------------------------------------------------------


@app.command()
def serve(
    host: str = typer.Option(None, "--host", help="Bind host"),
    port: int = typer.Option(None, "--port", help="Bind port"),
):
    """Start the REST API server."""
    import uvicorn

    from abcfood_fingerprint.api.app import create_app

    settings = get_settings()
    bind_host = host or settings.API_HOST
    bind_port = port or settings.API_PORT

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("FINGERPRINT-CTL SERVE MODE")
    logger.info("=" * 60)
    logger.info("Environment: %s", settings.ENVIRONMENT.upper())
    logger.info("API: http://%s:%d", bind_host, bind_port)
    logger.info("Docs: http://%s:%d/docs", bind_host, bind_port)
    logger.info("=" * 60)

    api_app = create_app()
    uvicorn.run(api_app, host=bind_host, port=bind_port, log_level="info")


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------


@app.command("test-connection")
def test_connection():
    """Test all connections (devices, S3, Odoo)."""
    from abcfood_fingerprint.core.device_manager import ping_device
    from abcfood_fingerprint.zk.pool import get_pool

    settings = get_settings()
    pool = get_pool()
    all_ok = True

    console.print("\n[bold]Testing connections...[/bold]\n")

    # Test devices
    for key in pool.device_keys():
        config = pool.get_config(key)
        try:
            ok = ping_device(key, pool)
            if ok:
                console.print(f"  [green]OK[/green]  Device {key} ({config.ip}:{config.port})")
            else:
                console.print(f"  [red]FAIL[/red]  Device {key} ({config.ip}:{config.port})")
                all_ok = False
        except Exception as e:
            console.print(f"  [red]FAIL[/red]  Device {key}: {e}")
            all_ok = False

    # Test S3
    if settings.S3_ACCESS_KEY:
        try:
            from abcfood_fingerprint.storage.s3 import S3Client

            s3 = S3Client()
            if s3.test_connection():
                console.print(f"  [green]OK[/green]  S3 ({settings.S3_BUCKET})")
            else:
                console.print(f"  [red]FAIL[/red]  S3 ({settings.S3_BUCKET})")
                all_ok = False
        except Exception as e:
            console.print(f"  [red]FAIL[/red]  S3: {e}")
            all_ok = False
    else:
        console.print("  [yellow]SKIP[/yellow]  S3 (not configured)")

    # Test Odoo
    if settings.ODOO_PASSWORD != "change-me":
        try:
            import odoorpc

            odoo = odoorpc.ODOO(
                settings.ODOO_HOST,
                protocol=settings.ODOO_PROTOCOL,
                port=settings.ODOO_PORT,
            )
            odoo.login(settings.ODOO_DB, settings.ODOO_USER, settings.ODOO_PASSWORD)
            console.print(f"  [green]OK[/green]  Odoo ({settings.ODOO_HOST})")
        except Exception as e:
            console.print(f"  [red]FAIL[/red]  Odoo: {e}")
            all_ok = False
    else:
        console.print("  [yellow]SKIP[/yellow]  Odoo (not configured)")

    console.print()
    if all_ok:
        console.print("[green]All connections OK[/green]")
    else:
        console.print("[red]Some connections failed[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Init check (for Docker init container)
# ---------------------------------------------------------------------------


@app.command("init-check")
def init_check(
    retry: int = typer.Option(3, "--retry", help="Number of retries"),
    retry_delay: int = typer.Option(5, "--retry-delay", help="Seconds between retries"),
):
    """Startup validation - verify all connections."""
    import time

    for attempt in range(1, retry + 1):
        console.print(f"\n[bold]Init check attempt {attempt}/{retry}[/bold]")
        try:
            test_connection()
            console.print("[green]Init check passed[/green]")
            return
        except SystemExit:
            if attempt < retry:
                console.print(f"[yellow]Retrying in {retry_delay}s...[/yellow]")
                time.sleep(retry_delay)

    console.print("[red]Init check failed after all retries[/red]")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------


@app.command()
def status():
    """Show current configuration and status."""
    settings = get_settings()

    table = Table(
        title="Fingerprint Service Configuration",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    rows = [
        ("Environment", settings.ENVIRONMENT),
        ("Machines Config", settings.ZK_MACHINES_CONFIG),
        ("API Host", f"{settings.API_HOST}:{settings.API_PORT}"),
        ("S3 Bucket", settings.S3_BUCKET),
        ("S3 Endpoint", settings.S3_ENDPOINT),
        ("Odoo Host", settings.ODOO_HOST),
        ("Odoo DB", settings.ODOO_DB),
        ("Telegram Configured", "Yes" if settings.TELEGRAM_BOT_TOKEN else "No"),
        ("Backup Retention", f"{settings.BACKUP_RETENTION_DAYS} days"),
        ("Log Level", settings.LOG_LEVEL),
    ]

    for label, value in rows:
        table.add_row(label, str(value))

    console.print(table)


# ---------------------------------------------------------------------------
# List command
# ---------------------------------------------------------------------------


@app.command("list")
def list_commands():
    """List all available commands."""
    table = Table(
        title="Available Commands",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
        expand=True,
        show_lines=True,
    )
    table.add_column("Command", style="cyan", width=40)
    table.add_column("Description", style="green", width=50)

    commands = [
        ("serve", "Start the REST API server"),
        ("status", "Show configuration"),
        ("test-connection", "Test all connections"),
        ("init-check", "Startup validation (Docker init)"),
        ("device list", "List all devices with status"),
        ("device info <key>", "Show detailed device info"),
        ("device ping <key>", "Ping a device"),
        ("device time <key>", "Get/sync device time"),
        ("device restart <key>", "Restart a device"),
        ("attendance get <key>", "Get attendance records"),
        ("attendance count <key>", "Count attendance records"),
        ("attendance live <key>", "Live attendance feed"),
        ("attendance clear <key>", "Clear attendance records"),
        ("user list <key>", "List users on device"),
        ("user get <key> <id>", "Get specific user"),
        ("user add <key>", "Add user to device"),
        ("user update <key> <uid>", "Update user on device"),
        ("user delete <key> <uid>", "Delete user from device"),
        ("user sync-from-odoo <key>", "Sync users from Odoo"),
        ("finger list <key>", "List fingerprint templates"),
        ("finger count <key>", "Count fingerprints"),
        ("finger backup <key>", "Backup fingerprints to S3"),
        ("finger restore <s3-key>", "Restore from S3 backup"),
        ("backup run <key>", "Full backup to S3"),
        ("backup list", "List S3 backups"),
        ("backup restore <s3-key>", "Restore from S3"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print("\n")
    console.print(table)
    console.print("\n")


if __name__ == "__main__":
    app()
