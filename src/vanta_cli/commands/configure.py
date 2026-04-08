"""Interactive configuration command for setting up user identity."""

from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.config import UserConfig, save_user_config
from vanta_cli.output import print_error, print_success


def configure(
    email: Optional[str] = typer.Option(None, "--email", help="Your email address in Vanta."),
) -> None:
    """Set up your Vanta CLI identity by matching your email to a Vanta user."""
    if not email:
        email = typer.prompt("Enter your email address in Vanta")

    client = VantaClient()

    typer.echo(f"Looking up user with email: {email}")
    matched_user = None
    for user in client.paginate("/users"):
        if user.get("email", "").lower() == email.lower():
            matched_user = user
            break

    if not matched_user:
        print_error(f"No active user found with email: {email}")
        raise typer.Exit(1)

    user_id = matched_user["id"]
    display_name = matched_user.get("displayName", "")

    typer.echo(f"\nFound user:")
    typer.echo(f"  ID:    {user_id}")
    typer.echo(f"  Name:  {display_name}")
    typer.echo(f"  Email: {email}")

    if not typer.confirm("\nSave this as your identity?", default=True):
        raise typer.Abort()

    config = UserConfig(user_id=user_id, email=email, display_name=display_name)
    path = save_user_config(config)
    print_success(f"Configuration saved to {path}")
