"""CLI commands for user management on devices."""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
import rich.box

app = typer.Typer(
    name="user",
    help="User management on fingerprint devices",
    add_completion=False,
)

console = Console()


@app.command("list")
def user_list(
    device: str = typer.Argument(help="Device key"),
):
    """List all users on a device."""
    from abcfood_fingerprint.core.user_sync import get_users

    users = get_users(device)

    table = Table(
        title=f"Users on {device} ({len(users)} total)",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("UID", justify="right", style="cyan")
    table.add_column("User ID", style="green")
    table.add_column("Name")
    table.add_column("Privilege", justify="right")
    table.add_column("Card", justify="right")

    privilege_map = {0: "User", 14: "Admin"}
    for u in sorted(users, key=lambda x: x.uid):
        table.add_row(
            str(u.uid),
            u.user_id,
            u.name,
            privilege_map.get(u.privilege, str(u.privilege)),
            str(u.card) if u.card else "",
        )

    console.print(table)


@app.command("get")
def user_get(
    device: str = typer.Argument(help="Device key"),
    user_id: str = typer.Argument(help="User ID to look up"),
):
    """Get a specific user from a device."""
    from abcfood_fingerprint.core.user_sync import get_user

    user = get_user(device, user_id)
    if not user:
        console.print(f"[red]User {user_id} not found on {device}[/red]")
        raise typer.Exit(1)

    table = Table(
        title=f"User {user_id} on {device}",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("UID", str(user.uid))
    table.add_row("User ID", user.user_id)
    table.add_row("Name", user.name)
    table.add_row("Privilege", str(user.privilege))
    table.add_row("Card", str(user.card))
    table.add_row("Group", user.group_id)

    console.print(table)


@app.command("add")
def user_add(
    device: str = typer.Argument(help="Device key"),
    uid: int = typer.Option(..., "--uid", help="Internal UID"),
    name: str = typer.Option(..., "--name", help="User name"),
    user_id: str = typer.Option("", "--user-id", help="User ID (identification_id)"),
    privilege: int = typer.Option(0, "--privilege", help="Privilege level (0=user, 14=admin)"),
    card: int = typer.Option(0, "--card", help="Card number"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm add"),
):
    """Add a user to a device."""
    if not confirm:
        console.print("[yellow]Use --confirm to add the user[/yellow]")
        raise typer.Exit(1)

    from abcfood_fingerprint.core.user_sync import add_user

    add_user(device, uid=uid, name=name, user_id=user_id, privilege=privilege, card=card)
    console.print(f"[green]User uid={uid} name={name} added to {device}[/green]")


@app.command("update")
def user_update(
    device: str = typer.Argument(help="Device key"),
    uid: int = typer.Argument(help="UID of user to update"),
    name: Optional[str] = typer.Option(None, "--name", help="New name"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="New user ID"),
    privilege: Optional[int] = typer.Option(None, "--privilege", help="New privilege"),
    card: Optional[int] = typer.Option(None, "--card", help="New card number"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm update"),
):
    """Update a user on a device."""
    if not confirm:
        console.print("[yellow]Use --confirm to update the user[/yellow]")
        raise typer.Exit(1)

    from abcfood_fingerprint.core.user_sync import update_user

    update_user(device, uid=uid, name=name, user_id=user_id, privilege=privilege, card=card)
    console.print(f"[green]User uid={uid} updated on {device}[/green]")


@app.command("delete")
def user_delete(
    device: str = typer.Argument(help="Device key"),
    uid: int = typer.Argument(help="UID of user to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm delete"),
):
    """Delete a user from a device."""
    if not confirm:
        console.print("[yellow]Use --confirm to delete the user[/yellow]")
        console.print("[red]WARNING: This will also delete the user's fingerprints![/red]")
        raise typer.Exit(1)

    from abcfood_fingerprint.core.user_sync import delete_user

    delete_user(device, uid)
    console.print(f"[green]User uid={uid} deleted from {device}[/green]")


@app.command("sync-from-odoo")
def user_sync_from_odoo(
    device: str = typer.Argument(help="Device key"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm sync (implies --no-dry-run)"),
):
    """Sync users from Odoo HRIS to a device."""
    if confirm:
        dry_run = False

    from abcfood_fingerprint.core.user_sync import sync_from_odoo

    result = sync_from_odoo(device, dry_run=dry_run)

    table = Table(
        title=f"User Sync {'(DRY RUN)' if dry_run else ''} - {device}",
        show_header=True,
        header_style="bold magenta",
        box=rich.box.ROUNDED,
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Odoo Employees", str(result["odoo_employees"]))
    table.add_row("Device Users", str(result["device_users"]))
    table.add_row("To Add", str(result["to_add"]))
    table.add_row("To Update", str(result["to_update"]))
    table.add_row("Unchanged", str(result["unchanged"]))

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry run - use --confirm to apply changes[/yellow]")
