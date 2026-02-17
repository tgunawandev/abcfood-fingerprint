"""CLI commands for backup operations."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
import rich.box

app = typer.Typer(
    name="backup",
    help="Backup and restore operations",
    add_completion=False,
)

console = Console()


@app.command("run")
def backup_run(
    device: str = typer.Argument(help="Device key to backup"),
):
    """Run a full backup (users + fingerprints) to S3."""
    from abcfood_fingerprint.core.backup import run_backup
    from abcfood_fingerprint.utils.notifications import notify_backup_success

    result = run_backup(device)

    console.print(f"[green]Backup complete for {device}[/green]")
    console.print(f"  Users: {result['user_count']}")
    console.print(f"  Fingerprints: {result['fingerprint_count']}")
    console.print(f"  S3 Key: [cyan]{result['s3_key']}[/cyan]")

    notify_backup_success(
        device=device,
        users=result["user_count"],
        fingerprints=result["fingerprint_count"],
        s3_key=result["s3_key"],
    )


@app.command("list")
def backup_list(
    device: Optional[str] = typer.Option(None, "--device", help="Filter by device"),
):
    """List available backups in S3."""
    from abcfood_fingerprint.core.backup import list_backups

    backups = list_backups(device)

    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        return

    table = Table(
        title=f"S3 Backups ({len(backups)} found)",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("Device", style="cyan")
    table.add_column("Filename", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Last Modified")
    table.add_column("S3 Key", style="dim")

    for b in backups:
        size_kb = b["size"] / 1024
        table.add_row(
            b["device"],
            b["filename"],
            f"{size_kb:.1f} KB",
            b["last_modified"],
            b["key"],
        )

    console.print(table)


@app.command("restore")
def backup_restore(
    backup_key: str = typer.Argument(help="S3 key of backup to restore"),
    target_device: Optional[str] = typer.Option(None, "--target", help="Target device"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm restore"),
):
    """Restore a backup from S3 to a device."""
    if confirm:
        dry_run = False

    from abcfood_fingerprint.core.backup import restore_backup

    result = restore_backup(backup_key, target_device=target_device, dry_run=dry_run)

    console.print(f"Restore {'(DRY RUN) ' if dry_run else ''}from: [cyan]{backup_key}[/cyan]")
    console.print(f"  Target: {result['target_device']}")
    console.print(f"  Users: {result['user_count']}")
    console.print(f"  Fingerprints: {result['fingerprint_count']}")

    if dry_run:
        console.print("\n[yellow]Dry run - use --confirm to apply[/yellow]")
    else:
        console.print("\n[green]Restore complete[/green]")
