"""CLI commands for attendance operations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
import rich.box

app = typer.Typer(
    name="attendance",
    help="Attendance record operations",
    add_completion=False,
)

console = Console()


@app.command("get")
def attendance_get(
    device: str = typer.Argument(help="Device key"),
    date_from: Optional[str] = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = typer.Option(None, "--to", help="End date (YYYY-MM-DD)"),
    limit: int = typer.Option(50, "--limit", help="Max records to display"),
):
    """Get attendance records from a device."""
    from abcfood_fingerprint.core.attendance import get_attendance

    dt_from = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
    dt_to = (
        datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        if date_to
        else None
    )

    records = get_attendance(device, dt_from, dt_to)

    table = Table(
        title=f"Attendance - {device} ({len(records)} records)",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("User ID", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("Status", justify="right")
    table.add_column("Punch", justify="right")

    for r in records[:limit]:
        table.add_row(
            r.user_id,
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            str(r.status),
            str(r.punch),
        )

    if len(records) > limit:
        table.add_row("...", f"({len(records) - limit} more)", "", "")

    console.print(table)


@app.command("count")
def attendance_count(
    device: str = typer.Argument(help="Device key"),
):
    """Count attendance records on a device."""
    from abcfood_fingerprint.core.attendance import count_attendance

    count = count_attendance(device)
    console.print(f"Device [cyan]{device}[/cyan]: [green]{count}[/green] attendance records")


@app.command("live")
def attendance_live(
    device: str = typer.Argument(help="Device key"),
):
    """Show live attendance feed (press Ctrl+C to stop)."""
    import time

    from abcfood_fingerprint.zk.pool import get_pool

    pool = get_pool()
    client = pool.get_client(device)
    console.print(f"[yellow]Listening for live attendance on {device}... (Ctrl+C to stop)[/yellow]")

    try:
        with client.connect() as c:
            from zk import ZK

            for attendance in c._conn.live_capture():
                if attendance is None:
                    continue
                console.print(
                    f"[cyan]{attendance.user_id}[/cyan] | "
                    f"[green]{attendance.timestamp}[/green] | "
                    f"Status: {attendance.status}"
                )
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped live capture[/yellow]")


@app.command("clear")
def attendance_clear(
    device: str = typer.Argument(help="Device key"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm clearing attendance"),
):
    """Clear all attendance records from a device."""
    if not confirm:
        console.print("[yellow]Use --confirm to clear attendance records[/yellow]")
        console.print("[red]WARNING: This will delete all attendance data on the device![/red]")
        raise typer.Exit(1)

    from abcfood_fingerprint.core.attendance import clear_attendance

    clear_attendance(device)
    console.print(f"[green]Attendance cleared on device {device}[/green]")
