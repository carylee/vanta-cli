from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)

PERSON_COLUMNS = [
    ("id", "ID"),
    ("emailAddress", "Email"),
    ("name.display", "Name"),
    ("employment.status", "Status"),
    ("tasksSummary.status", "Tasks"),
]


@app.command("list")
def list_people(
    search: Optional[str] = typer.Option(
        None, "--search", "-q", help="Filter by email, first name, or last name."
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s",
        help="Employment status: UPCOMING, CURRENT, ON_LEAVE, INACTIVE, FORMER.",
    ),
    group: Optional[str] = typer.Option(None, "--group", help="Filter by group ID."),
    tasks_status: Optional[str] = typer.Option(
        None, "--tasks-status", help="Filter by tasks summary status."
    ),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all people in the organization."""
    client = VantaClient()
    params: dict = {}
    if search:
        params["emailAndNameFilter"] = search
    if status:
        params["employmentStatus"] = status
    if group:
        params["groupIdsMatchesAny"] = group
    if tasks_status:
        params["tasksSummaryStatusMatchesAny"] = tasks_status
    items = list(client.paginate("/people", params=params, limit=limit))
    print_list(items, PERSON_COLUMNS, title="People")


@app.command("get")
def get_person(
    person_id: str = typer.Argument(help="Person ID."),
) -> None:
    """Get details for a specific person."""
    client = VantaClient()
    data = client.get(f"/people/{person_id}")
    print_detail(data.get("results", data), title=f"Person: {person_id}")


@app.command("update")
def update_person(
    person_id: str = typer.Argument(help="Person ID to update."),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Employment start date (ISO)."),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="Employment end date (ISO)."),
) -> None:
    """Update a person's metadata."""
    client = VantaClient()
    body: dict = {}
    if start_date is not None:
        body["startDate"] = start_date
    if end_date is not None:
        body["endDate"] = end_date
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/people/{person_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Person: {person_id}")


@app.command("set-leave")
def set_leave(
    person_id: str = typer.Argument(help="Person ID."),
    start_date: str = typer.Option(..., "--start-date", help="Leave start date (ISO)."),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="Leave end date (ISO)."),
) -> None:
    """Set leave information for a person. Replaces existing leave info."""
    client = VantaClient()
    body: dict = {"startDate": start_date}
    if end_date:
        body["endDate"] = end_date
    data = client.post(f"/people/{person_id}/set-leave", json=body)
    print_detail(data.get("results", data), title=f"Person: {person_id}")


@app.command("clear-leave")
def clear_leave(
    person_id: str = typer.Argument(help="Person ID."),
) -> None:
    """Remove leave information for a person, making them active again."""
    client = VantaClient()
    data = client.post(f"/people/{person_id}/clear-leave")
    print_detail(data.get("results", data), title=f"Person: {person_id}")


@app.command("offboard")
def offboard(
    person_ids: list[str] = typer.Argument(help="Person IDs to offboard."),
) -> None:
    """Offboard one or more people. Requires ex-employee status and deactivated accounts."""
    client = VantaClient()
    data = client.post("/people/offboard", json={"personIds": person_ids})
    results = data.get("results", [])
    if isinstance(results, list):
        for r in results:
            status = r.get("status", "UNKNOWN")
            print_success(f"  {status}: {r.get('data', r.get('error', ''))}")
    else:
        print_detail(data, title="Offboard Results")


@app.command("mark-as-people")
def mark_as_people(
    person_ids: list[str] = typer.Argument(help="Person IDs to mark as people."),
) -> None:
    """Mark accounts as people so they can be assigned tasks and used in tests."""
    client = VantaClient()
    data = client.post("/people/mark-as-people", json={"personIds": person_ids})
    print_success(f"Marked {len(person_ids)} account(s) as people.")


@app.command("mark-as-not-people")
def mark_as_not_people(
    person_ids: list[str] = typer.Argument(help="Person IDs to mark as not people."),
) -> None:
    """Mark accounts as not people. They won't be used in personnel-related tests."""
    client = VantaClient()
    data = client.post("/people/mark-as-not-people", json={"personIds": person_ids})
    print_success(f"Marked {len(person_ids)} account(s) as not people.")
