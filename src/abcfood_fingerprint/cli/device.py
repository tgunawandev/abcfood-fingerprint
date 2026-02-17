"""CLI commands for device management."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
import rich.box

app = typer.Typer(
    name="device",
    help="Device management commands",
    add_completion=False,
)

console = Console()


@app.command("list")
def device_list():
    """List all configured devices with status."""
    from abcfood_fingerprint.core.device_manager import get_all_device_statuses

    statuses = get_all_device_statuses()

    table = Table(
        title="Fingerprint Devices",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("IP:Port", style="yellow")
    table.add_column("Model")
    table.add_column("Serial")
    table.add_column("Status", style="bold")
    table.add_column("Users", justify="right")
    table.add_column("Attendance", justify="right")

    for s in statuses:
        status_str = "[green]ONLINE[/green]" if s.online else "[red]OFFLINE[/red]"
        users = str(s.info.user_count) if s.info else "-"
        att = str(s.info.attendance_count) if s.info else "-"
        table.add_row(
            s.key,
            s.config.name,
            f"{s.config.ip}:{s.config.port}",
            s.config.model,
            s.config.serial,
            status_str,
            users,
            att,
        )

    console.print(table)


@app.command("info")
def device_info(
    device: str = typer.Argument(help="Device key (e.g., tmi, outsourcing)"),
):
    """Show detailed device information."""
    from abcfood_fingerprint.core.device_manager import get_device_status

    status = get_device_status(device)

    if not status.online:
        console.print(f"[red]Device {device} is OFFLINE: {status.error}[/red]")
        raise typer.Exit(1)

    info = status.info
    table = Table(
        title=f"Device: {status.config.name}",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Key", status.key)
    table.add_row("Name", status.config.name)
    table.add_row("IP", f"{status.config.ip}:{status.config.port}")
    table.add_row("Model", status.config.model)
    table.add_row("Config Serial", status.config.serial)
    if info:
        table.add_row("Firmware", info.firmware_version)
        table.add_row("Device Serial", info.serial_number)
        table.add_row("Platform", info.platform)
        table.add_row("Device Name", info.device_name)
        table.add_row("MAC Address", info.mac_address)
        table.add_row("Users", str(info.user_count))
        table.add_row("Fingerprints", str(info.fp_count))
        table.add_row("Attendance Records", str(info.attendance_count))
        table.add_row("Device Time", str(info.device_time) if info.device_time else "N/A")

    console.print(table)


@app.command("ping")
def device_ping(
    device: str = typer.Argument(help="Device key"),
):
    """Ping a device to check connectivity."""
    from abcfood_fingerprint.core.device_manager import ping_device

    if ping_device(device):
        console.print(f"[green]Device {device} is reachable[/green]")
    else:
        console.print(f"[red]Device {device} is unreachable[/red]")
        raise typer.Exit(1)


@app.command("time")
def device_time(
    device: str = typer.Argument(help="Device key"),
    sync: bool = typer.Option(False, "--sync", help="Sync device time to system time"),
):
    """Get or sync device time."""
    from abcfood_fingerprint.core.device_manager import get_device_time, sync_device_time
    from datetime import datetime

    if sync:
        sync_device_time(device)
        console.print(f"[green]Time synced on {device} to {datetime.now()}[/green]")
    else:
        dt = get_device_time(device)
        if dt:
            console.print(f"Device time: [cyan]{dt}[/cyan]")
            console.print(f"System time: [cyan]{datetime.now()}[/cyan]")
        else:
            console.print("[red]Failed to get device time[/red]")


@app.command("restart")
def device_restart(
    device: str = typer.Argument(help="Device key"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm restart"),
):
    """Restart a device."""
    if not confirm:
        console.print("[yellow]Use --confirm to restart the device[/yellow]")
        raise typer.Exit(1)

    from abcfood_fingerprint.core.device_manager import restart_device

    restart_device(device)
    console.print(f"[green]Device {device} restarted[/green]")
