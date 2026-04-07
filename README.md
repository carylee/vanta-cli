# vanta-cli

A command-line interface for the [Vanta](https://www.vanta.com/) compliance API. Covers all 122 API endpoints across 19 resource groups.

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and install
git clone <repo-url> && cd vanta-cli
uv sync

# Configure credentials
cp .env.example .env
# Edit .env with your Vanta OAuth credentials
```

Your `.env` needs three values:

```
VANTA_OAUTH_CLIENT_ID=vci_...
VANTA_OAUTH_CLIENT_SECRET=vcs_...
VANTA_ORGANIZATION=your-org
```

OAuth credentials are created in the Vanta dashboard under **Settings > API > OAuth2 Clients**.

## Usage

```bash
# List all commands
vanta --help

# Browse compliance posture
vanta frameworks list
vanta tests list --status NEEDS_ATTENTION
vanta controls list --framework soc2

# Justify a non-compliant code change
vanta tests entities list github-code-change-automated-checks-enabled
vanta tests entities deactivate github-code-change-automated-checks-enabled <entity-id> \
  --reason "Dependency update with manual review"

# Manage vendors
vanta vendors list --name "AWS"
vanta vendors get <vendor-id>

# Browse people
vanta people list --search "jane" --status CURRENT

# Check vulnerabilities
vanta vulnerabilities list --severity HIGH
```

### Output formats

All commands support `--output` / `-o` to control output format:

```bash
vanta tests list -o table   # Rich table (default)
vanta tests list -o json    # JSON array, pipe to jq
vanta tests list -o jsonl   # One JSON object per line
```

### Pagination

List commands auto-paginate through all results. Use `--limit` to cap the number of items returned:

```bash
vanta people list --limit 10
```

## Command groups

| Command | Description |
|---|---|
| `controls` | Manage compliance controls, library, linked docs/tests |
| `customer-trust` | Accounts, questionnaires, exports, tag categories |
| `discovered-vendors` | Browse auto-discovered vendors, promote to managed |
| `documents` | Manage documents, file uploads, links |
| `frameworks` | Browse compliance frameworks (read-only) |
| `groups` | Manage groups and membership |
| `integrations` | Browse integrations and resource kinds |
| `monitored-computers` | Browse monitored computers (read-only) |
| `people` | Manage people, leave, offboarding |
| `policies` | Browse policies (read-only) |
| `risk-scenarios` | Manage risk scenarios and approval workflows |
| `tests` | Manage tests and test entity justifications |
| `trust-centers` | Manage trust center, resources, subscribers, FAQs, updates |
| `users` | Browse active users (read-only) |
| `vendor-risk-attributes` | Browse vendor risk attributes (read-only) |
| `vendors` | Manage vendors, findings, security reviews |
| `vulnerabilities` | Manage vulnerabilities, bulk deactivate/reactivate |
| `vulnerable-assets` | Browse vulnerable assets (read-only) |
| `vulnerability-remediations` | Browse remediations, acknowledge SLA misses |

Run `vanta <command> --help` for full details on any command.

## Authentication

The CLI uses OAuth2 client credentials to obtain a Bearer token. Tokens are cached at `~/.cache/vanta-cli/token.json` and automatically refreshed when they expire (~1 hour).

Scopes requested: `vanta-api.all:read vanta-api.all:write`.
