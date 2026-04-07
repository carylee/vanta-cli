from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list

app = typer.Typer(no_args_is_help=True)

USER_COLUMNS = [
    ("id", "ID"),
    ("displayName", "Name"),
    ("email", "Email"),
    ("isActive", "Active"),
]


@app.command("list")
def list_users(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List all active users."""
    client = VantaClient()
    items = list(client.paginate("/users", limit=limit))
    print_list(items, USER_COLUMNS, title="Users")


@app.command("get")
def get_user(
    user_id: str = typer.Argument(help="User ID."),
) -> None:
    """Get user details."""
    client = VantaClient()
    data = client.get(f"/users/{user_id}")
    print_detail(data.get("results", data), title=f"User: {user_id}")
