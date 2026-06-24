- Always use `uv` for python
- Example .env is avialable with the same structure in .env.example and can be read with python-dotenv

## Working with the Vanta API/CLI

### Get raw data via the client, not CLI tables
The CLI prints Rich tables that **truncate** IDs, URLs, and long fields. For any
real data work, call the client directly and inspect JSON:

```python
uv run python -c "from vanta_cli.client import VantaClient; import json; \
c=VantaClient(); print(json.dumps(list(c.paginate('/vulnerabilities', params={'isDeactivated':'false'})), indent=2, default=str))"
```

`VantaClient` methods: `get`, `post`, `patch`, `paginate(path, params=, limit=)`.
For raw status codes (probing schemas), use `c._http.request(method, path, headers=c._headers(), json=body)`.

### Test entities carry no source linkage — cross-reference GitHub
Test entities (`/tests/{testId}/entities`) only have `id`, `displayName`,
`responseType`, dates — **no repo, PR number, or URL**. To map them back:
- PRs: `gh search prs --owner <org> "<title words>"` — special chars (notably `:`)
  break the search; strip them and use a few distinctive words.
- Vulnerabilities: don't use test entities — use the `/vulnerabilities` resource
  (below), which has an authoritative `externalURL`.

### Two different deactivation paths (don't mix them up)
- **Test entities** (PRs, repos): `POST /tests/{testId}/entities/{entityId}/deactivate`
  → returns **202 (async)**. The status change is **not** immediate and the CLI
  prints "Deactivated" on any 2xx, so verify later via the DEACTIVATED list.
  Entity IDs are prefixed, e.g. `GithubPullRequest-<hex>`, `GithubRepo-<hex>`.
- **Vulnerabilities** (the `packages-checked-for-vulnerabilities-*` / Dependabot
  tests): these are **not** test entities — the entity deactivate endpoint 404s.
  Use the `/vulnerabilities` resource: `POST /vulnerabilities/deactivate` with
  `{"updates":[{"id", "deactivateReason", "shouldReactivateWhenFixable", "deactivateUntilDate"?}]}`
  → returns **200 (sync)** with per-id `results`. `shouldReactivateWhenFixable`
  is **required** by the API. The vulnerability `id` equals the test entity's hex.

### Vulnerabilities: repo attribution and filtering
- Each `/vulnerabilities` object has `externalURL` like
  `https://github.com/<org>/<repo>/security/dependabot/<n>` — the authoritative
  repo. Use this to resolve the same CVE appearing in multiple repos (test
  entities can't be told apart; vulnerability records can).
- Filter active vs. deactivated with `isDeactivated=true|false` (NOT
  `deactivationStatus`, which is silently ignored).

### Inventory ownership (`inventory-list-owners` test, SOC 2 6.17)
Failing entities are unowned resources (e.g. `GithubRepo-<hex>`). Assign an owner
(don't deactivate) via:
`PATCH /integrations/{integrationId}/resource-kinds/{resourceKind}/resources`
with `{"updates":[{"id","ownerId","description"?,"inScope"?}]}` (≤50 per call;
owners must be CURRENT users). `ownerId` is a Vanta user id — resolve emails via
`/users` (fields: `id`, `email`, `displayName`, `isActive`). The same endpoint
sets `inScope` to scope a resource out of monitoring.

### Async deactivations re-run on Vanta's schedule
202 (test-entity) deactivations and any test re-run take a while to reflect —
don't block waiting on the test to flip; verify the entity moved to DEACTIVATED.

### Known CLI gaps (as of 2026-06)
- `vanta vulnerabilities deactivate` omits the required `shouldReactivateWhenFixable`
  (always 400s) — fix in flight on branch `fix-vulnerabilities-deactivate`.
- `vanta integrations resource-kinds list <id>` crashes (`'list' object has no
  attribute 'get'`) — handler assumes a dict, API returns a list.
- No command to set resource owners — PATCH the resources endpoint directly.
