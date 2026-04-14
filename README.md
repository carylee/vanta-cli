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

## TUI

Launch an interactive terminal UI to browse resources and review staged changes:

```bash
vanta tui
```

The TUI provides a sidebar for navigating resource groups, paginated tables with search (`/`) and filters (`f`), and a dedicated changeset review screen for staged changes. The changeset screen includes:

- **Detail pane** showing the full request body of the highlighted change
- **Parsed columns** breaking API paths into readable Path, Entity, and Action fields
- **Auto-generated summaries** from request bodies when descriptions are empty
- **Batch select** with `space` to toggle individual rows and `s` to select/deselect all
- **Progress indicator** and rate limiting during batch apply

## Profiles

Use `--profile` to switch between execution modes:

```bash
# Default profile: reads and writes execute immediately
vanta tests entities deactivate my-test <entity-id> --reason "..."

# Agent profile: writes are staged for review instead of executed
vanta --profile agent tests entities deactivate my-test <entity-id> --reason "..."
```

You can also set the profile via the `VANTA_PROFILE` environment variable:

```bash
export VANTA_PROFILE=agent
```

| Profile | Scopes | Behavior |
|---|---|---|
| `default` | `read` + `write` | Writes execute immediately |
| `agent` | `read` only | Writes are staged to `vanta-export/changeset.json` |

### Changeset commands

Review and apply staged changes from the command line:

```bash
vanta changeset list              # List all staged changes
vanta changeset show <id>         # Show details of a staged change
vanta changeset apply <id>        # Apply a single staged change
vanta changeset drop <id>         # Drop a single staged change
vanta changeset clear             # Clear all staged changes
```

Or use `vanta tui` and navigate to **Staged Changes** for an interactive review experience.

## Authentication

The CLI uses OAuth2 client credentials to obtain a Bearer token. Tokens are cached at `~/.cache/vanta-cli/token.json` (per profile) and automatically refreshed when they expire (~1 hour). If a token expires mid-session, the CLI transparently fetches a fresh one and retries the request.

Scopes requested depend on the active profile (see [Profiles](#profiles) above).
