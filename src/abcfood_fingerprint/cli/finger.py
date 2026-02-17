"""CLI commands for fingerprint template operations."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
import rich.box

app = typer.Typer(
    name="finger",
    help="Fingerprint template operations",
    add_completion=False,
)

console = Console()


@app.command("list")
def finger_list(
    device: str = typer.Argument(help="Device key"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Filter by user ID"),
):
    """List fingerprint templates on a device."""
    from abcfood_fingerprint.core.fingerprint import get_fingerprints

    templates = get_fingerprints(device, user_id=user_id)

    table = Table(
        title=f"Fingerprints on {device} ({len(templates)} templates)",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("UID", justify="right", style="cyan")
    table.add_column("User ID", style="green")
    table.add_column("Finger", justify="right")
    table.add_column("Template Size", justify="right")

    finger_names = {
        0: "R-Thumb", 1: "R-Index", 2: "R-Middle", 3: "R-Ring", 4: "R-Little",
        5: "L-Thumb", 6: "L-Index", 7: "L-Middle", 8: "L-Ring", 9: "L-Little",
    }

    for t in sorted(templates, key=lambda x: (x.uid, x.finger_index)):
        table.add_row(
            str(t.uid),
            t.user_id,
            finger_names.get(t.finger_index, str(t.finger_index)),
            f"{len(t.template)} B",
        )

    console.print(table)


@app.command("count")
def finger_count(
    device: str = typer.Argument(help="Device key"),
):
    """Count fingerprint templates on a device."""
    from abcfood_fingerprint.core.fingerprint import count_fingerprints, get_fingerprint_summary

    total = count_fingerprints(device)
    summary = get_fingerprint_summary(device)

    console.print(f"Device [cyan]{device}[/cyan]: [green]{total}[/green] fingerprints")
    console.print(f"Users with fingerprints: [green]{len(summary)}[/green]")


@app.command("backup")
def finger_backup(
    device: str = typer.Argument(help="Device key"),
):
    """Backup fingerprint templates to S3."""
    from abcfood_fingerprint.core.backup import run_backup

    result = run_backup(device)

    console.print(f"[green]Backup complete for {device}[/green]")
    console.print(f"  Users: {result['user_count']}")
    console.print(f"  Fingerprints: {result['fingerprint_count']}")
    console.print(f"  S3 Key: [cyan]{result['s3_key']}[/cyan]")


@app.command("restore")
def finger_restore(
    backup_key: str = typer.Argument(help="S3 key of backup to restore"),
    target_device: Optional[str] = typer.Option(None, "--target", help="Target device (default: original)"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm restore (implies --no-dry-run)"),
):
    """Restore fingerprint templates from S3 backup."""
    if confirm:
        dry_run = False

    from abcfood_fingerprint.core.backup import restore_backup

    result = restore_backup(backup_key, target_device=target_device, dry_run=dry_run)

    console.print(f"Restore {'(DRY RUN) ' if dry_run else ''}from: [cyan]{backup_key}[/cyan]")
    console.print(f"  Target device: {result['target_device']}")
    console.print(f"  Users: {result['user_count']}")
    console.print(f"  Fingerprints: {result['fingerprint_count']}")

    if dry_run:
        console.print("\n[yellow]Dry run - use --confirm to apply[/yellow]")
    else:
        console.print("\n[green]Restore complete[/green]")
