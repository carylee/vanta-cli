from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)

RISK_COLUMNS = [
    ("riskId", "Risk ID"),
    ("description", "Description"),
    ("treatment", "Treatment"),
    ("likelihood", "Likelihood"),
    ("impact", "Impact"),
]


@app.command("list")
def list_risk_scenarios(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List risk scenarios."""
    client = VantaClient()
    items = list(client.paginate("/risk-scenarios", limit=limit))
    print_list(items, RISK_COLUMNS, title="Risk Scenarios")


@app.command("get")
def get_risk_scenario(
    risk_id: str = typer.Argument(help="Risk scenario ID."),
) -> None:
    """Get a risk scenario."""
    client = VantaClient()
    data = client.get(f"/risk-scenarios/{risk_id}")
    print_detail(data.get("results", data), title=f"Risk Scenario: {risk_id}")


@app.command("create")
def create_risk_scenario(
    description: str = typer.Option(..., "--description", help="Risk description."),
    treatment: Optional[str] = typer.Option(None, "--treatment", help="Treatment: Mitigate, Transfer, Avoid, Accept."),
    likelihood: Optional[float] = typer.Option(None, "--likelihood", help="Likelihood score."),
    impact: Optional[float] = typer.Option(None, "--impact", help="Impact score."),
    owner: Optional[str] = typer.Option(None, "--owner", help="Owner user ID."),
    risk_type: Optional[str] = typer.Option(None, "--type", help="Type: 'Risk Scenario' or 'Enterprise Risk'."),
    note: Optional[str] = typer.Option(None, "--note", help="Additional notes."),
    sensitive: bool = typer.Option(False, "--sensitive", help="Mark as sensitive (restricted visibility)."),
) -> None:
    """Create a risk scenario."""
    client = VantaClient()
    body: dict = {"description": description}
    if treatment:
        body["treatment"] = treatment
    if likelihood is not None:
        body["likelihood"] = likelihood
    if impact is not None:
        body["impact"] = impact
    if owner:
        body["owner"] = owner
    if risk_type:
        body["type"] = risk_type
    if note:
        body["note"] = note
    if sensitive:
        body["isSensitive"] = True
    data = client.post("/risk-scenarios", json=body)
    print_detail(data.get("results", data), title="Created Risk Scenario")


@app.command("update")
def update_risk_scenario(
    risk_id: str = typer.Argument(help="Risk scenario ID."),
    description: Optional[str] = typer.Option(None, "--description", help="New description."),
    treatment: Optional[str] = typer.Option(None, "--treatment", help="New treatment."),
    likelihood: Optional[float] = typer.Option(None, "--likelihood", help="New likelihood."),
    impact: Optional[float] = typer.Option(None, "--impact", help="New impact."),
    owner: Optional[str] = typer.Option(None, "--owner", help="New owner user ID."),
    note: Optional[str] = typer.Option(None, "--note", help="New note."),
) -> None:
    """Update a risk scenario."""
    client = VantaClient()
    body: dict = {}
    if description is not None:
        body["description"] = description
    if treatment is not None:
        body["treatment"] = treatment
    if likelihood is not None:
        body["likelihood"] = likelihood
    if impact is not None:
        body["impact"] = impact
    if owner is not None:
        body["owner"] = owner
    if note is not None:
        body["note"] = note
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/risk-scenarios/{risk_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Risk Scenario: {risk_id}")


@app.command("submit-for-approval")
def submit_for_approval(
    risk_id: str = typer.Argument(help="Risk scenario ID."),
) -> None:
    """Submit a risk scenario for approval."""
    client = VantaClient()
    client.post(f"/risk-scenarios/{risk_id}/submit-for-approval")
    print_success(f"Submitted risk scenario {risk_id} for approval")


@app.command("cancel-approval")
def cancel_approval(
    risk_id: str = typer.Argument(help="Risk scenario ID."),
) -> None:
    """Cancel an approval request for a risk scenario."""
    client = VantaClient()
    client.post(f"/risk-scenarios/{risk_id}/cancel-approval-request")
    print_success(f"Cancelled approval request for risk scenario {risk_id}")
