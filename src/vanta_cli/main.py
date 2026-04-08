import sys
from typing import Optional

import typer
from rich.console import Console

from vanta_cli.config import Settings
from vanta_cli.output import OutputFormat, set_format

# Module-level settings, populated by the callback before subcommands run.
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the active Settings instance (populated by the main callback)."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings

app = typer.Typer(
    help="Vanta CLI - manage your compliance program from the terminal.",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    output: Optional[OutputFormat] = typer.Option(
        None, "--output", "-o", help="Output format: table, json, jsonl"
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Auth profile: 'default' (read-write) or 'agent' (read-only, stages writes)."
    ),
) -> None:
    global _settings
    if output is not None:
        set_format(output)
    _settings = Settings.load(profile=profile)
    if ctx.invoked_subcommand is None:
        from vanta_cli.tui.app import VantaTUI

        VantaTUI().run()


@app.command()
def tui() -> None:
    """Launch the interactive TUI for browsing Vanta data."""
    from vanta_cli.tui.app import VantaTUI

    VantaTUI().run()


# Register standalone commands
from vanta_cli.commands.configure import configure  # noqa: E402

app.command("configure", help="Set up your Vanta CLI identity.")(configure)

# Register command groups
from vanta_cli.commands.controls import app as controls_app  # noqa: E402
from vanta_cli.commands.customer_trust import app as customer_trust_app  # noqa: E402
from vanta_cli.commands.discovered_vendors import app as discovered_vendors_app  # noqa: E402
from vanta_cli.commands.documents import app as documents_app  # noqa: E402
from vanta_cli.commands.frameworks import app as frameworks_app  # noqa: E402
from vanta_cli.commands.groups import app as groups_app  # noqa: E402
from vanta_cli.commands.integrations import app as integrations_app  # noqa: E402
from vanta_cli.commands.monitored_computers import app as computers_app  # noqa: E402
from vanta_cli.commands.people import app as people_app  # noqa: E402
from vanta_cli.commands.policies import app as policies_app  # noqa: E402
from vanta_cli.commands.risk_scenarios import app as risk_app  # noqa: E402
from vanta_cli.commands.tests import app as tests_app  # noqa: E402
from vanta_cli.commands.trust_centers import app as trust_centers_app  # noqa: E402
from vanta_cli.commands.users import app as users_app  # noqa: E402
from vanta_cli.commands.vendor_risk_attributes import app as risk_attrs_app  # noqa: E402
from vanta_cli.commands.vendors import app as vendors_app  # noqa: E402
from vanta_cli.commands.vulnerabilities import app as vulns_app  # noqa: E402
from vanta_cli.commands.vulnerable_assets import app as vuln_assets_app  # noqa: E402
from vanta_cli.commands.changeset import app as changeset_app  # noqa: E402
from vanta_cli.commands.vulnerability_remediations import app as vuln_remediations_app  # noqa: E402

app.add_typer(changeset_app, name="changeset", help="Review and apply staged changes from agent mode.")
app.add_typer(controls_app, name="controls", help="Manage compliance controls.")
app.add_typer(customer_trust_app, name="customer-trust", help="Manage customer trust accounts and questionnaires.")
app.add_typer(discovered_vendors_app, name="discovered-vendors", help="Browse discovered vendors.")
app.add_typer(documents_app, name="documents", help="Manage compliance documents.")
app.add_typer(frameworks_app, name="frameworks", help="Browse compliance frameworks.")
app.add_typer(groups_app, name="groups", help="Manage groups and membership.")
app.add_typer(integrations_app, name="integrations", help="Browse integrations and resources.")
app.add_typer(computers_app, name="monitored-computers", help="Browse monitored computers.")
app.add_typer(people_app, name="people", help="Manage people and personnel.")
app.add_typer(policies_app, name="policies", help="Browse policies.")
app.add_typer(risk_app, name="risk-scenarios", help="Manage risk scenarios.")
app.add_typer(tests_app, name="tests", help="Manage compliance tests and test entities.")
app.add_typer(trust_centers_app, name="trust-centers", help="Manage trust centers.")
app.add_typer(users_app, name="users", help="Browse users.")
app.add_typer(risk_attrs_app, name="vendor-risk-attributes", help="Browse vendor risk attributes.")
app.add_typer(vendors_app, name="vendors", help="Manage vendors and risk.")
app.add_typer(vulns_app, name="vulnerabilities", help="Manage vulnerabilities.")
app.add_typer(vuln_assets_app, name="vulnerable-assets", help="Browse vulnerable assets.")
app.add_typer(vuln_remediations_app, name="vulnerability-remediations", help="Manage vulnerability remediations.")


def cli() -> None:
    """Entry point that catches WriteIntercepted for friendly output."""
    try:
        app()
    except SystemExit:
        raise
    except Exception as exc:
        from vanta_cli.client import WriteIntercepted

        if isinstance(exc, WriteIntercepted):
            console = Console(stderr=True)
            console.print(
                f"[yellow]Change staged[/yellow] ({exc.entry['id']}): "
                f"{exc.entry['method']} {exc.entry['path']}"
            )
            console.print(
                "[dim]Run 'vanta changeset list' to review, "
                "'vanta changeset apply' to execute.[/dim]"
            )
            sys.exit(3)
        raise
