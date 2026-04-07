from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)

VULN_COLUMNS = [
    ("id", "ID"),
    ("externalVulnerabilityId", "External ID"),
    ("severity", "Severity"),
    ("packageIdentifier", "Package"),
    ("isDeactivated", "Deactivated"),
]


@app.command("list")
def list_vulnerabilities(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query."),
    severity: Optional[str] = typer.Option(
        None, "--severity", "-s", help="Filter: CRITICAL, HIGH, MEDIUM, LOW."
    ),
    is_deactivated: Optional[bool] = typer.Option(None, "--deactivated/--active", help="Filter by deactivation status."),
    is_fix_available: Optional[bool] = typer.Option(None, "--fix-available/--no-fix", help="Filter by fix availability."),
    package: Optional[str] = typer.Option(None, "--package", help="Filter by package identifier."),
    integration: Optional[str] = typer.Option(None, "--integration", help="Filter by scanner integration ID."),
    asset_id: Optional[str] = typer.Option(None, "--asset-id", help="Filter by vulnerable asset ID."),
    sla_before: Optional[str] = typer.Option(None, "--sla-before", help="SLA deadline before date (ISO)."),
    sla_after: Optional[str] = typer.Option(None, "--sla-after", help="SLA deadline after date (ISO)."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List vulnerabilities."""
    client = VantaClient()
    params: dict = {}
    if query:
        params["q"] = query
    if severity:
        params["severity"] = severity
    if is_deactivated is not None:
        params["isDeactivated"] = str(is_deactivated).lower()
    if is_fix_available is not None:
        params["isFixAvailable"] = str(is_fix_available).lower()
    if package:
        params["packageIdentifier"] = package
    if integration:
        params["integrationId"] = integration
    if asset_id:
        params["vulnerableAssetId"] = asset_id
    if sla_before:
        params["slaDeadlineBeforeDate"] = sla_before
    if sla_after:
        params["slaDeadlineAfterDate"] = sla_after
    items = list(client.paginate("/vulnerabilities", params=params, limit=limit))
    print_list(items, VULN_COLUMNS, title="Vulnerabilities")


@app.command("get")
def get_vulnerability(
    vulnerability_id: str = typer.Argument(help="Vulnerability ID."),
) -> None:
    """Get details for a specific vulnerability."""
    client = VantaClient()
    data = client.get(f"/vulnerabilities/{vulnerability_id}")
    print_detail(data.get("results", data), title=f"Vulnerability: {vulnerability_id}")


@app.command("deactivate")
def deactivate(
    ids: list[str] = typer.Argument(help="Vulnerability IDs to deactivate."),
    reason: str = typer.Option(..., "--reason", "-r", help="Reason for deactivation."),
    until: Optional[str] = typer.Option(None, "--until", help="Auto-reactivate date (ISO)."),
) -> None:
    """Deactivate one or more vulnerabilities."""
    client = VantaClient()
    updates = []
    for vid in ids:
        entry: dict = {"id": vid, "deactivateReason": reason}
        if until:
            entry["deactivateUntilDate"] = until
        updates.append(entry)
    client.post("/vulnerabilities/deactivate", json={"updates": updates})
    print_success(f"Deactivated {len(ids)} vulnerability(ies)")


@app.command("reactivate")
def reactivate(
    ids: list[str] = typer.Argument(help="Vulnerability IDs to reactivate."),
) -> None:
    """Reactivate one or more vulnerabilities."""
    client = VantaClient()
    updates = [{"id": vid} for vid in ids]
    client.post("/vulnerabilities/reactivate", json={"updates": updates})
    print_success(f"Reactivated {len(ids)} vulnerability(ies)")
