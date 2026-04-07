from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list

app = typer.Typer(no_args_is_help=True)

COMPUTER_COLUMNS = [
    ("id", "ID"),
    ("serialNumber", "Serial"),
    ("operatingSystem.type", "OS"),
    ("owner.displayName", "Owner"),
    ("lastCheckDate", "Last Check"),
]


@app.command("list")
def list_computers(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List monitored computers."""
    client = VantaClient()
    items = list(client.paginate("/monitored-computers", limit=limit))
    print_list(items, COMPUTER_COLUMNS, title="Monitored Computers")


@app.command("get")
def get_computer(
    computer_id: str = typer.Argument(help="Computer ID."),
) -> None:
    """Get details for a monitored computer."""
    client = VantaClient()
    data = client.get(f"/monitored-computers/{computer_id}")
    print_detail(data.get("results", data), title=f"Computer: {computer_id}")
