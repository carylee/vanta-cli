"""Commands for reviewing and applying staged changesets."""

from __future__ import annotations

import json

import typer
from rich.console import Console

from vanta_cli.changeset import load_changeset, drop_change, clear_changeset
from vanta_cli.client import VantaClient
from vanta_cli.config import Settings
from vanta_cli.output import print_detail, print_error, print_list, print_success

console = Console()

app = typer.Typer(no_args_is_help=True)

CHANGESET_COLUMNS = [
    ("id", "ID"),
    ("method", "Method"),
    ("path", "Path"),
    ("description", "Description"),
    ("timestamp", "Timestamp"),
]


@app.command("list")
def list_changes() -> None:
    """List all staged changes."""
    changes = load_changeset()
    if not changes:
        print("No staged changes.")
        raise typer.Exit(0)
    print_list(changes, CHANGESET_COLUMNS, title="Staged Changes")


@app.command("show")
def show_change(
    change_id: str = typer.Argument(help="Change ID to show."),
) -> None:
    """Show details of a staged change."""
    changes = load_changeset()
    for c in changes:
        if c["id"] == change_id:
            print_detail(c, title=f"Change: {change_id}")
            if c.get("body"):
                console.print("\n[bold]Request body:[/bold]")
                console.print(json.dumps(c["body"], indent=2))
            return
    print_error(f"Change {change_id} not found.")
    raise typer.Exit(1)


@app.command("apply")
def apply_changes(
    change_id: str = typer.Argument(None, help="Change ID to apply. Omit to apply all."),
) -> None:
    """Apply staged changes using the default (read-write) profile."""
    changes = load_changeset()
    if not changes:
        print("No staged changes to apply.")
        raise typer.Exit(0)

    if change_id:
        to_apply = [c for c in changes if c["id"] == change_id]
        if not to_apply:
            print_error(f"Change {change_id} not found.")
            raise typer.Exit(1)
    else:
        to_apply = changes

    # Always use default profile for applying changes
    settings = Settings.load(profile="default")
    client = VantaClient(settings=settings)

    applied_ids = []
    for change in to_apply:
        method = change["method"]
        path = change["path"]
        body = change.get("body")
        desc = change.get("description", f"{method} {path}")

        try:
            if method == "POST":
                client.post(path, json=body)
            elif method == "PATCH":
                client.patch(path, json=body)
            elif method == "DELETE":
                client.delete(path)
            elif method == "PUT":
                client.put(path, json=body)
            else:
                print_error(f"Unknown method {method} for change {change['id']}")
                continue
            print_success(f"Applied: {desc}")
            applied_ids.append(change["id"])
        except Exception as e:
            print_error(f"Failed to apply {change['id']}: {e}")

    # Remove applied changes from the changeset
    if applied_ids:
        remaining = [c for c in load_changeset() if c["id"] not in applied_ids]
        from vanta_cli.changeset import save_changeset
        save_changeset(remaining)
        print_success(f"\nApplied {len(applied_ids)} change(s).")


@app.command("drop")
def drop(
    change_id: str = typer.Argument(help="Change ID to discard."),
) -> None:
    """Discard a single staged change."""
    if drop_change(change_id):
        print_success(f"Dropped change {change_id}")
    else:
        print_error(f"Change {change_id} not found.")
        raise typer.Exit(1)


@app.command("clear")
def clear() -> None:
    """Discard all staged changes."""
    changes = load_changeset()
    if not changes:
        print("No staged changes to clear.")
        raise typer.Exit(0)
    clear_changeset()
    print_success(f"Cleared {len(changes)} staged change(s).")
