from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_list

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def list_risk_attributes(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List vendor risk attributes."""
    client = VantaClient()
    items = list(client.paginate("/vendor-risk-attributes", limit=limit))
    print_list(items, [("id", "ID"), ("name", "Name"), ("description", "Description")], title="Vendor Risk Attributes")
