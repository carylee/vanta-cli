from pathlib import Path
from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)

# Sub-resource apps
access_requests_app = typer.Typer(no_args_is_help=True, help="Manage access requests.")
controls_app = typer.Typer(no_args_is_help=True, help="Manage trust center controls.")
categories_app = typer.Typer(no_args_is_help=True, help="Manage control categories.")
faqs_app = typer.Typer(no_args_is_help=True, help="Manage FAQs.")
resources_app = typer.Typer(no_args_is_help=True, help="Manage trust center resources/documents.")
subprocessors_app = typer.Typer(no_args_is_help=True, help="Manage subprocessors.")
subscribers_app = typer.Typer(no_args_is_help=True, help="Manage subscribers.")
subscriber_groups_app = typer.Typer(no_args_is_help=True, help="Manage subscriber groups.")
updates_app = typer.Typer(no_args_is_help=True, help="Manage trust center updates.")
viewers_app = typer.Typer(no_args_is_help=True, help="Manage viewers.")

app.add_typer(access_requests_app, name="access-requests")
app.add_typer(controls_app, name="controls")
app.add_typer(categories_app, name="categories")
app.add_typer(faqs_app, name="faqs")
app.add_typer(resources_app, name="resources")
app.add_typer(subprocessors_app, name="subprocessors")
app.add_typer(subscribers_app, name="subscribers")
app.add_typer(subscriber_groups_app, name="subscriber-groups")
app.add_typer(updates_app, name="updates")
app.add_typer(viewers_app, name="viewers")


# --- Core ---


@app.command("get")
def get_trust_center(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
) -> None:
    """Get trust center details."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}")
    print_detail(data.get("results", data), title=f"Trust Center: {slug_id}")


@app.command("update")
def update_trust_center(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    title: Optional[str] = typer.Option(None, "--title", help="Custom title."),
    description: Optional[str] = typer.Option(None, "--description", help="Company description."),
    is_public: Optional[bool] = typer.Option(None, "--public/--private", help="Public visibility."),
    privacy_policy: Optional[str] = typer.Option(None, "--privacy-policy", help="Privacy policy URL."),
) -> None:
    """Update trust center settings."""
    client = VantaClient()
    body: dict = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["companyDescription"] = description
    if is_public is not None:
        body["isPublic"] = is_public
    if privacy_policy is not None:
        body["privacyPolicy"] = privacy_policy
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/trust-centers/{slug_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Trust Center: {slug_id}")


@app.command("activity")
def list_activity(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    event_types: Optional[str] = typer.Option(None, "--event-types", help="Filter by event types (comma-separated)."),
    after: Optional[str] = typer.Option(None, "--after", help="Events after date (ISO)."),
    before: Optional[str] = typer.Option(None, "--before", help="Events before date (ISO)."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List trust center activity events."""
    client = VantaClient()
    params: dict = {}
    if event_types:
        params["eventTypesMatchesAny"] = event_types
    if after:
        params["afterDate"] = after
    if before:
        params["beforeDate"] = before
    items = list(client.paginate(f"/trust-centers/{slug_id}/activity", params=params, limit=limit))
    print_list(items, [("id", "ID"), ("eventType", "Type"), ("createdAt", "Date")], title="Activity")


@app.command("historical-access-requests")
def list_historical_access_requests(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List historical access requests."""
    client = VantaClient()
    items = list(client.paginate(f"/trust-centers/{slug_id}/historical-access-requests", limit=limit))
    print_list(items, [("id", "ID"), ("email", "Email"), ("status", "Status"), ("createdAt", "Date")], title="Historical Access Requests")


# --- Access Requests ---


@access_requests_app.command("list")
def list_access_requests(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List pending access requests."""
    client = VantaClient()
    items = list(client.paginate(f"/trust-centers/{slug_id}/access-requests", limit=limit))
    print_list(items, [("id", "ID"), ("email", "Email"), ("companyName", "Company"), ("createdAt", "Date")], title="Access Requests")


@access_requests_app.command("get")
def get_access_request(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    request_id: str = typer.Argument(help="Access request ID."),
) -> None:
    """Get an access request."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/access-requests/{request_id}")
    print_detail(data.get("results", data), title=f"Access Request: {request_id}")


@access_requests_app.command("approve")
def approve_access_request(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    request_id: str = typer.Argument(help="Access request ID."),
    access_level: Optional[str] = typer.Option(None, "--access-level", help="FULL_ACCESS or PARTIAL_ACCESS."),
    nda_required: Optional[bool] = typer.Option(None, "--nda/--no-nda", help="Require NDA."),
    expiration: Optional[str] = typer.Option(None, "--expiration", help="Expiration date (ISO)."),
) -> None:
    """Approve an access request."""
    client = VantaClient()
    body: dict = {}
    if access_level:
        body["accessLevel"] = access_level
    if nda_required is not None:
        body["isNdaRequired"] = nda_required
    if expiration:
        body["expirationDate"] = expiration
    client.post(f"/trust-centers/{slug_id}/access-requests/{request_id}/approve", json=body)
    print_success(f"Approved access request {request_id}")


@access_requests_app.command("deny")
def deny_access_request(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    request_id: str = typer.Argument(help="Access request ID."),
) -> None:
    """Deny an access request."""
    client = VantaClient()
    client.post(f"/trust-centers/{slug_id}/access-requests/{request_id}/deny")
    print_success(f"Denied access request {request_id}")


# --- Controls ---


@controls_app.command("list")
def list_controls(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List trust center controls."""
    client = VantaClient()
    items = list(client.paginate(f"/trust-centers/{slug_id}/controls", limit=limit))
    print_list(items, [("id", "ID"), ("name", "Name"), ("description", "Description")], title="Trust Center Controls")


@controls_app.command("get")
def get_control(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    control_id: str = typer.Argument(help="Control ID."),
) -> None:
    """Get a trust center control."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/controls/{control_id}")
    print_detail(data.get("results", data), title=f"Control: {control_id}")


@controls_app.command("add")
def add_control(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    control_id: str = typer.Option(..., "--control-id", help="Control ID to add."),
    category_ids: list[str] = typer.Option(..., "--category-id", help="Category IDs (repeatable)."),
) -> None:
    """Add a control to the trust center."""
    client = VantaClient()
    client.post(f"/trust-centers/{slug_id}/controls", json={"controlId": control_id, "categoryIds": category_ids})
    print_success(f"Added control {control_id}")


@controls_app.command("remove")
def remove_control(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    control_id: str = typer.Argument(help="Control ID to remove."),
) -> None:
    """Remove a control from the trust center."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/controls/{control_id}")
    print_success(f"Removed control {control_id}")


# --- Control Categories ---


@categories_app.command("list")
def list_categories(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
) -> None:
    """List control categories."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/control-categories")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("id", "ID"), ("name", "Name")], title="Control Categories")


@categories_app.command("get")
def get_category(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    category_id: str = typer.Argument(help="Category ID."),
) -> None:
    """Get a control category."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/control-categories/{category_id}")
    print_detail(data.get("results", data), title=f"Category: {category_id}")


@categories_app.command("create")
def create_category(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    name: str = typer.Option(..., "--name", help="Category name."),
) -> None:
    """Create a control category."""
    client = VantaClient()
    data = client.post(f"/trust-centers/{slug_id}/control-categories", json={"name": name})
    print_detail(data.get("results", data), title="Created Category")


@categories_app.command("update")
def update_category(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    category_id: str = typer.Argument(help="Category ID."),
    name: str = typer.Option(..., "--name", help="New name."),
) -> None:
    """Update a control category."""
    client = VantaClient()
    data = client.patch(f"/trust-centers/{slug_id}/control-categories/{category_id}", json={"name": name})
    print_detail(data.get("results", data), title=f"Updated Category: {category_id}")


@categories_app.command("delete")
def delete_category(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    category_id: str = typer.Argument(help="Category ID to delete."),
) -> None:
    """Delete a control category."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/control-categories/{category_id}")
    print_success(f"Deleted category {category_id}")


# --- FAQs ---


@faqs_app.command("list")
def list_faqs(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
) -> None:
    """List FAQs."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/faqs")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("id", "ID"), ("question", "Question"), ("answer", "Answer")], title="FAQs")


@faqs_app.command("get")
def get_faq(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    faq_id: str = typer.Argument(help="FAQ ID."),
) -> None:
    """Get a FAQ."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/faqs/{faq_id}")
    print_detail(data.get("results", data), title=f"FAQ: {faq_id}")


@faqs_app.command("create")
def create_faq(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    question: str = typer.Option(..., "--question", "-q", help="FAQ question."),
    answer: str = typer.Option(..., "--answer", "-a", help="FAQ answer."),
) -> None:
    """Create a FAQ."""
    client = VantaClient()
    data = client.post(f"/trust-centers/{slug_id}/faqs", json={"question": question, "answer": answer})
    print_detail(data.get("results", data), title="Created FAQ")


@faqs_app.command("update")
def update_faq(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    faq_id: str = typer.Argument(help="FAQ ID."),
    question: Optional[str] = typer.Option(None, "--question", "-q", help="New question."),
    answer: Optional[str] = typer.Option(None, "--answer", "-a", help="New answer."),
) -> None:
    """Update a FAQ."""
    client = VantaClient()
    body: dict = {}
    if question is not None:
        body["question"] = question
    if answer is not None:
        body["answer"] = answer
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/trust-centers/{slug_id}/faqs/{faq_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated FAQ: {faq_id}")


@faqs_app.command("delete")
def delete_faq(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    faq_id: str = typer.Argument(help="FAQ ID to delete."),
) -> None:
    """Delete a FAQ."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/faqs/{faq_id}")
    print_success(f"Deleted FAQ {faq_id}")


# --- Resources ---


@resources_app.command("list")
def list_resources(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
) -> None:
    """List trust center resources."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/resources")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("id", "ID"), ("title", "Title"), ("isPublic", "Public"), ("description", "Description")], title="Resources")


@resources_app.command("get")
def get_resource(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    resource_id: str = typer.Argument(help="Resource ID."),
) -> None:
    """Get a resource."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/resources/{resource_id}")
    print_detail(data.get("results", data), title=f"Resource: {resource_id}")


@resources_app.command("create")
def create_resource(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    file: Path = typer.Option(..., "--file", "-f", help="File to upload.", exists=True),
    title: Optional[str] = typer.Option(None, "--title", help="Resource title."),
    description: Optional[str] = typer.Option(None, "--description", help="Resource description."),
    is_public: bool = typer.Option(False, "--public/--private", help="Public visibility."),
) -> None:
    """Upload a new resource."""
    client = VantaClient()
    fields: dict[str, str] = {"isPublic": str(is_public).lower()}
    if title:
        fields["title"] = title
    if description:
        fields["description"] = description
    data = client.upload(f"/trust-centers/{slug_id}/resources", file, fields=fields)
    print_detail(data.get("results", data) if data else {"status": "uploaded"}, title="Created Resource")


@resources_app.command("update")
def update_resource(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    resource_id: str = typer.Argument(help="Resource ID."),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    description: Optional[str] = typer.Option(None, "--description", help="New description."),
    is_public: Optional[bool] = typer.Option(None, "--public/--private", help="Public visibility."),
) -> None:
    """Update a resource."""
    client = VantaClient()
    body: dict = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if is_public is not None:
        body["isPublic"] = is_public
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/trust-centers/{slug_id}/resources/{resource_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Resource: {resource_id}")


@resources_app.command("delete")
def delete_resource(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    resource_id: str = typer.Argument(help="Resource ID to delete."),
) -> None:
    """Delete a resource."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/resources/{resource_id}")
    print_success(f"Deleted resource {resource_id}")


@resources_app.command("download")
def download_resource(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    resource_id: str = typer.Argument(help="Resource ID."),
    output: Path = typer.Option(..., "--output", "-o", help="Destination file path."),
) -> None:
    """Download a resource file."""
    client = VantaClient()
    dest = client.download(f"/trust-centers/{slug_id}/resources/{resource_id}/media", output)
    print_success(f"Downloaded to {dest}")


# --- Subprocessors ---


@subprocessors_app.command("list")
def list_subprocessors(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
) -> None:
    """List subprocessors."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/subprocessors")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("id", "ID"), ("name", "Name"), ("purpose", "Purpose"), ("location", "Location")], title="Subprocessors")


@subprocessors_app.command("get")
def get_subprocessor(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    subprocessor_id: str = typer.Argument(help="Subprocessor ID."),
) -> None:
    """Get a subprocessor."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/subprocessors/{subprocessor_id}")
    print_detail(data.get("results", data), title=f"Subprocessor: {subprocessor_id}")


@subprocessors_app.command("create")
def create_subprocessor(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    name: str = typer.Option(..., "--name", help="Subprocessor name."),
    url: Optional[str] = typer.Option(None, "--url", help="Subprocessor URL."),
    description: Optional[str] = typer.Option(None, "--description", help="Description."),
    location: Optional[str] = typer.Option(None, "--location", help="Location."),
    purpose: Optional[str] = typer.Option(None, "--purpose", help="Purpose."),
) -> None:
    """Create a subprocessor."""
    client = VantaClient()
    body: dict = {"name": name}
    if url:
        body["url"] = url
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if purpose:
        body["purpose"] = purpose
    data = client.post(f"/trust-centers/{slug_id}/subprocessors", json=body)
    print_detail(data.get("results", data), title="Created Subprocessor")


@subprocessors_app.command("update")
def update_subprocessor(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    subprocessor_id: str = typer.Argument(help="Subprocessor ID."),
    description: Optional[str] = typer.Option(None, "--description", help="New description."),
    location: Optional[str] = typer.Option(None, "--location", help="New location."),
    purpose: Optional[str] = typer.Option(None, "--purpose", help="New purpose."),
) -> None:
    """Update a subprocessor."""
    client = VantaClient()
    body: dict = {}
    if description is not None:
        body["description"] = description
    if location is not None:
        body["location"] = location
    if purpose is not None:
        body["purpose"] = purpose
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/trust-centers/{slug_id}/subprocessors/{subprocessor_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Subprocessor: {subprocessor_id}")


@subprocessors_app.command("delete")
def delete_subprocessor(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    subprocessor_id: str = typer.Argument(help="Subprocessor ID to delete."),
) -> None:
    """Delete a subprocessor."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/subprocessors/{subprocessor_id}")
    print_success(f"Deleted subprocessor {subprocessor_id}")


# --- Subscribers ---


@subscribers_app.command("list")
def list_subscribers(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    account_id: Optional[str] = typer.Option(None, "--account-id", help="Filter by customer trust account ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List subscribers."""
    client = VantaClient()
    params: dict = {}
    if account_id:
        params["customerTrustAccountId"] = account_id
    items = list(client.paginate(f"/trust-centers/{slug_id}/subscribers", params=params, limit=limit))
    print_list(items, [("id", "ID"), ("email", "Email"), ("isVerified", "Verified")], title="Subscribers")


@subscribers_app.command("get")
def get_subscriber(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    subscriber_id: str = typer.Argument(help="Subscriber ID."),
) -> None:
    """Get a subscriber."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/subscribers/{subscriber_id}")
    print_detail(data.get("results", data), title=f"Subscriber: {subscriber_id}")


@subscribers_app.command("add")
def add_subscriber(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    email: str = typer.Option(..., "--email", help="Subscriber email."),
    account_id: Optional[str] = typer.Option(None, "--account-id", help="Customer trust account ID."),
    skip_verification: bool = typer.Option(False, "--skip-verification", help="Skip email verification."),
) -> None:
    """Add a subscriber."""
    client = VantaClient()
    body: dict = {"email": email}
    if account_id:
        body["customerTrustAccountId"] = account_id
    if skip_verification:
        body["shouldSkipEmailVerification"] = True
    data = client.post(f"/trust-centers/{slug_id}/subscribers", json=body)
    print_detail(data.get("results", data), title="Added Subscriber")


@subscribers_app.command("remove")
def remove_subscriber(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    subscriber_id: str = typer.Argument(help="Subscriber ID."),
) -> None:
    """Remove a subscriber."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/subscribers/{subscriber_id}")
    print_success(f"Removed subscriber {subscriber_id}")


@subscribers_app.command("set-groups")
def set_subscriber_groups(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    subscriber_id: str = typer.Argument(help="Subscriber ID."),
    group_ids: list[str] = typer.Argument(help="Group IDs to assign."),
) -> None:
    """Set group membership for a subscriber."""
    client = VantaClient()
    client.put(f"/trust-centers/{slug_id}/subscribers/{subscriber_id}/groups", json={"groupIds": group_ids})
    print_success(f"Updated groups for subscriber {subscriber_id}")


# --- Subscriber Groups ---


@subscriber_groups_app.command("list")
def list_subscriber_groups(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List subscriber groups."""
    client = VantaClient()
    items = list(client.paginate(f"/trust-centers/{slug_id}/subscriber-groups", limit=limit))
    print_list(items, [("id", "ID"), ("name", "Name")], title="Subscriber Groups")


@subscriber_groups_app.command("get")
def get_subscriber_group(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    group_id: str = typer.Argument(help="Subscriber group ID."),
) -> None:
    """Get a subscriber group."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/subscriber-groups/{group_id}")
    print_detail(data.get("results", data), title=f"Subscriber Group: {group_id}")


@subscriber_groups_app.command("create")
def create_subscriber_group(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    name: str = typer.Option(..., "--name", help="Group name."),
    subscriber_ids: Optional[list[str]] = typer.Option(None, "--subscriber-id", help="Subscriber IDs (repeatable)."),
) -> None:
    """Create a subscriber group."""
    client = VantaClient()
    body: dict = {"name": name, "subscriberIds": subscriber_ids or []}
    data = client.post(f"/trust-centers/{slug_id}/subscriber-groups", json=body)
    print_detail(data.get("results", data), title="Created Subscriber Group")


@subscriber_groups_app.command("update")
def update_subscriber_group(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    group_id: str = typer.Argument(help="Subscriber group ID."),
    name: str = typer.Option(..., "--name", help="New name."),
) -> None:
    """Update a subscriber group."""
    client = VantaClient()
    data = client.patch(f"/trust-centers/{slug_id}/subscriber-groups/{group_id}", json={"name": name})
    print_detail(data.get("results", data), title=f"Updated Group: {group_id}")


@subscriber_groups_app.command("delete")
def delete_subscriber_group(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    group_id: str = typer.Argument(help="Subscriber group ID to delete."),
) -> None:
    """Delete a subscriber group."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/subscriber-groups/{group_id}")
    print_success(f"Deleted subscriber group {group_id}")


# --- Updates ---


@updates_app.command("list")
def list_updates(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List trust center updates."""
    client = VantaClient()
    items = list(client.paginate(f"/trust-centers/{slug_id}/updates", limit=limit))
    print_list(items, [("id", "ID"), ("title", "Title"), ("category", "Category"), ("createdAt", "Created")], title="Updates")


@updates_app.command("get")
def get_update(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    update_id: str = typer.Argument(help="Update ID."),
) -> None:
    """Get an update."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/updates/{update_id}")
    print_detail(data.get("results", data), title=f"Update: {update_id}")


@updates_app.command("create")
def create_update(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    title: str = typer.Option(..., "--title", help="Update title."),
    description: str = typer.Option(..., "--description", help="Update description."),
    category: str = typer.Option(..., "--category", help="Category: GENERAL, COMPLIANCE, SECURITY, PRIVACY, INCIDENT, ROADMAP."),
) -> None:
    """Create a trust center update."""
    client = VantaClient()
    body = {"title": title, "description": description, "category": category}
    data = client.post(f"/trust-centers/{slug_id}/updates", json=body)
    print_detail(data.get("results", data), title="Created Update")


@updates_app.command("update")
def edit_update(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    update_id: str = typer.Argument(help="Update ID."),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    description: Optional[str] = typer.Option(None, "--description", help="New description."),
    category: Optional[str] = typer.Option(None, "--category", help="New category."),
) -> None:
    """Edit an update."""
    client = VantaClient()
    body: dict = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if category is not None:
        body["category"] = category
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/trust-centers/{slug_id}/updates/{update_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated: {update_id}")


@updates_app.command("delete")
def delete_update(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    update_id: str = typer.Argument(help="Update ID to delete."),
) -> None:
    """Delete an update."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/updates/{update_id}")
    print_success(f"Deleted update {update_id}")


@updates_app.command("notify-all")
def notify_all_subscribers(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    update_id: str = typer.Argument(help="Update ID."),
) -> None:
    """Notify all subscribers about an update."""
    client = VantaClient()
    client.post(f"/trust-centers/{slug_id}/updates/{update_id}/notify-all-subscribers")
    print_success(f"Notified all subscribers about update {update_id}")


@updates_app.command("notify-specific")
def notify_specific(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    update_id: str = typer.Argument(help="Update ID."),
    emails: Optional[list[str]] = typer.Option(None, "--email", help="Email addresses (repeatable)."),
    group_ids: Optional[list[str]] = typer.Option(None, "--group-id", help="Subscriber group IDs (repeatable)."),
) -> None:
    """Notify specific subscribers about an update."""
    client = VantaClient()
    body: dict = {"emails": emails or [], "subscriberGroupIds": group_ids or []}
    client.post(f"/trust-centers/{slug_id}/updates/{update_id}/notify-specific-subscribers", json=body)
    print_success(f"Sent notifications for update {update_id}")


# --- Viewers ---


@viewers_app.command("list")
def list_viewers(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    include_removed: Optional[bool] = typer.Option(None, "--include-removed", help="Include removed viewers."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List viewers."""
    client = VantaClient()
    params: dict = {}
    if include_removed is not None:
        params["includeRemoved"] = str(include_removed).lower()
    items = list(client.paginate(f"/trust-centers/{slug_id}/viewers", params=params, limit=limit))
    print_list(items, [("id", "ID"), ("email", "Email"), ("name", "Name"), ("accessLevel", "Access")], title="Viewers")


@viewers_app.command("get")
def get_viewer(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    viewer_id: str = typer.Argument(help="Viewer ID."),
) -> None:
    """Get a viewer."""
    client = VantaClient()
    data = client.get(f"/trust-centers/{slug_id}/viewers/{viewer_id}")
    print_detail(data.get("results", data), title=f"Viewer: {viewer_id}")


@viewers_app.command("add")
def add_viewer(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    email: str = typer.Option(..., "--email", help="Viewer email."),
    name: str = typer.Option(..., "--name", help="Viewer name."),
    company: str = typer.Option(..., "--company", help="Viewer's company name."),
    access_level: str = typer.Option(..., "--access-level", help="FULL_ACCESS or PARTIAL_ACCESS."),
    nda_required: bool = typer.Option(False, "--nda", help="Require NDA."),
    expiration: Optional[str] = typer.Option(None, "--expiration", help="Access expiration date (ISO)."),
) -> None:
    """Add a viewer to the trust center."""
    client = VantaClient()
    body: dict = {
        "email": email,
        "name": name,
        "companyName": company,
        "accessLevel": access_level,
        "isNdaRequired": nda_required,
    }
    if expiration:
        body["expirationDate"] = expiration
    data = client.post(f"/trust-centers/{slug_id}/viewers", json=body)
    print_detail(data.get("results", data), title="Added Viewer")


@viewers_app.command("remove")
def remove_viewer(
    slug_id: str = typer.Argument(help="Trust center slug ID."),
    viewer_id: str = typer.Argument(help="Viewer ID."),
) -> None:
    """Remove a viewer."""
    client = VantaClient()
    client.delete(f"/trust-centers/{slug_id}/viewers/{viewer_id}")
    print_success(f"Removed viewer {viewer_id}")
