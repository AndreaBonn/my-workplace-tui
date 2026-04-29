**English** | [Italiano](README.it.md)

# Workspace TUI

Terminal interface for Gmail, Google Chat, Google Calendar, Google Drive, and Jira.

<div align="center">

[![CI](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/my-workplace-tui/main/badges/test-badge.json)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/my-workplace-tui/main/badges/coverage-badge.json)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-policy-green.svg)](SECURITY.md)

</div>

Workspace TUI is a keyboard-driven terminal application that brings Google Workspace and Jira into a single tabbed interface. Instead of juggling browser tabs, you get email, chat, calendar, files, issue tracking, cross-service search, and an overview dashboard all from your terminal.

## Features

**Gmail** — Read, compose, reply, forward, star, archive, and delete messages. View threads, download attachments, open in browser. Folder navigation.

**Google Chat** — Browse spaces and direct messages. Send messages. If the Chat API isn't enabled by your Workspace admin, the tab shows a message instead of failing.

**Google Calendar** — View events for the next 30 days. Create events with attendees. Meeting detection with video call link support.

**Google Drive** — Browse and search files. Download and upload. Filter by file type. Distinguish internal vs external shares based on your Workspace domain.

**Jira** — List, create, and inspect issues. Log work, transition statuses, add comments. Epic tracking via parent field. Saved JQL filters on F1-F9. Multi-account support for working across multiple Jira instances.

**Global Search** — Query Gmail, Jira, Drive, and Chat in parallel from a single search bar.

**Dashboard** — Shows unread emails, upcoming meetings, recent tasks, and task status breakdown. When Jira is not configured, the Jira sections are hidden.

**Background polling** — Periodic checks for new emails, calendar events, chat messages, and Jira updates. State-diffing to avoid notification spam on restart. OS desktop notifications on Linux (via plyer).

**Local cache** — API responses are cached locally via diskcache with configurable TTL per service, so repeated navigation doesn't hit the API every time.

## Installation

Requirements: Python 3.11+, a terminal with at least 120x30 characters and 256-color support. Linux (tested on Ubuntu 22.04+).

```bash
git clone https://github.com/AndreaBonn/my-workplace-tui.git
cd my-workplace-tui
./install.sh
```

The install script:
1. Verifies Python 3.11+
2. Installs [uv](https://docs.astral.sh/uv/) if not present (interactive prompt)
3. Installs dependencies via `uv sync`
4. Creates `credentials/` directory
5. Creates `.env` from `.env.example`
6. Creates the `workspace-tui` launcher in `~/.local/bin/`

If `~/.local/bin` is not in your PATH, add this to your `.bashrc` or `.zshrc`:

```bash
export PATH="${HOME}/.local/bin:${PATH}"
```

## Usage

```bash
workspace-tui
```

Or from the project directory:

```bash
uv run python -m workspace_tui
```

## Setup

### Google Cloud (one-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (or select an existing one)
3. Enable these APIs: **Gmail**, **Google Chat**, **Google Calendar**, **Google Drive**
4. Go to **Credentials** > **Create Credentials** > **OAuth client ID**
5. Select **Desktop application** as the application type
6. Download the JSON file and save it as `credentials/client_secret.json`
7. On first launch, the browser opens for OAuth2 authorization. The token is saved automatically in `credentials/token.json`

The OAuth2 scopes include write access (e.g., `gmail.modify`, `calendar`, `drive`) because the app can send emails, create events, and upload files. See [ASSUMPTIONS.md](ASSUMPTIONS.md) for the rationale.

### Jira (optional)

1. Generate an API token at [Atlassian account settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Set `JIRA_USERNAME`, `JIRA_API_TOKEN`, and `JIRA_BASE_URL` in `.env`

If Jira is not configured, the Jira tab shows a placeholder and the dashboard hides Jira sections. Everything else works normally.

#### Multi-account Jira

To connect multiple Jira instances, use `JIRA_ACCOUNTS` instead of `JIRA_BASE_URL`:

```env
JIRA_USERNAME=your.email@company.com
JIRA_API_TOKEN=your-api-token

JIRA_ACCOUNTS=acme,widgets

JIRA_ACME_BASE_URL=https://acme.atlassian.net
JIRA_ACME_DEFAULT_PROJECT=PROJ

JIRA_WIDGETS_BASE_URL=https://widgets.atlassian.net
JIRA_WIDGETS_DEFAULT_PROJECT=WDG
```

Account names are arbitrary. For each name, the app reads `JIRA_{NAME}_BASE_URL` and `JIRA_{NAME}_DEFAULT_PROJECT` (name uppercased). Search queries fan out to all accounts in parallel.

## Configuration

All settings live in `.env` (created from `.env.example` during installation). Edit it with any text editor.

### .env guide

```env
# ── Google OAuth2 ────────────────────────────────────────────
# Path to the client_secret.json downloaded from Google Cloud Console.
GOOGLE_CLIENT_SECRET_PATH=credentials/client_secret.json

# If you use multiple Google accounts in the browser, set this to the email
# you want Google links (Gmail, Calendar) to open with. Leave empty to use
# the browser default.
GOOGLE_ACCOUNT_EMAIL=

# ── Gmail ────────────────────────────────────────────────────
# How often to check for new emails (seconds, minimum 10).
GMAIL_POLL_INTERVAL=60

# ── Google Chat ──────────────────────────────────────────────
CHAT_POLL_INTERVAL=30

# ── Google Calendar ──────────────────────────────────────────
CALENDAR_POLL_INTERVAL=300

# ── Google Drive ─────────────────────────────────────────────
# Your Google Workspace domain (e.g. "company.com"). Used to tell apart
# internal shares from external ones. Leave empty to skip this distinction.
WORKSPACE_DOMAIN=

# Where to save downloaded files.
DRIVE_DOWNLOAD_DIR=~/Scaricati

# ── Notifications ────────────────────────────────────────────
# Desktop notifications for new emails, events, and Jira updates.
# Requires a notification daemon on Linux (e.g. dunst, mako).
NOTIFICATIONS_ENABLED=true

# ── Cache ────────────────────────────────────────────────────
# Local cache for API responses. Speeds up navigation and reduces API calls.
CACHE_ENABLED=true
CACHE_TTL=300

# ── Jira (optional) ─────────────────────────────────────────
# Your Atlassian account email.
JIRA_USERNAME=

# API token generated from Atlassian account settings.
JIRA_API_TOKEN=

# Single-account mode: set the instance URL directly.
JIRA_BASE_URL=
JIRA_DEFAULT_PROJECT=

# Multi-account mode: comma-separated names. See README for details.
# JIRA_ACCOUNTS=acme,widgets
# JIRA_ACME_BASE_URL=https://acme.atlassian.net
# JIRA_ACME_DEFAULT_PROJECT=PROJ

# How often to check for Jira updates (seconds, minimum 10).
JIRA_POLL_INTERVAL=120

# Set to true only for local development Jira instances without HTTPS.
JIRA_ALLOW_HTTP=false

# ── Saved JQL Filters ───────────────────────────────────────
# Quick-access filters bound to F1-F9 in the Jira tab.
# Example: JIRA_SAVED_JQL_1=assignee = currentUser() AND status = "In Progress"
JIRA_SAVED_JQL_1=
JIRA_SAVED_JQL_2=
JIRA_SAVED_JQL_3=
JIRA_SAVED_JQL_4=
JIRA_SAVED_JQL_5=
JIRA_SAVED_JQL_6=
JIRA_SAVED_JQL_7=
JIRA_SAVED_JQL_8=
JIRA_SAVED_JQL_9=
```

### Configuration reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLIENT_SECRET_PATH` | Path to OAuth2 client secret JSON | `credentials/client_secret.json` |
| `GOOGLE_ACCOUNT_EMAIL` | Force Google links to open with this account | — |
| `GMAIL_POLL_INTERVAL` | Gmail polling interval in seconds | `60` |
| `CHAT_POLL_INTERVAL` | Chat polling interval in seconds | `30` |
| `CALENDAR_POLL_INTERVAL` | Calendar polling interval in seconds | `300` |
| `WORKSPACE_DOMAIN` | Google Workspace domain for share filtering | — |
| `DRIVE_DOWNLOAD_DIR` | Download directory for Drive files | `~/Scaricati` |
| `NOTIFICATIONS_ENABLED` | Desktop notifications on/off | `true` |
| `CACHE_ENABLED` | Local response cache on/off | `true` |
| `CACHE_TTL` | Cache TTL in seconds | `300` |
| `JIRA_USERNAME` | Atlassian email | — |
| `JIRA_API_TOKEN` | Jira API token | — |
| `JIRA_BASE_URL` | Jira instance URL (single-account) | — |
| `JIRA_DEFAULT_PROJECT` | Default project key (single-account) | — |
| `JIRA_ACCOUNTS` | Comma-separated account names (multi-account) | — |
| `JIRA_POLL_INTERVAL` | Jira polling interval in seconds | `120` |
| `JIRA_ALLOW_HTTP` | Allow non-HTTPS Jira connections | `false` |
| `JIRA_SAVED_JQL_1` .. `_9` | Saved JQL filters for F1-F9 | — |

All polling intervals have a minimum of 10 seconds. Values below 10 are clamped automatically.

## Keyboard shortcuts

### Global

| Key | Action |
|-----|--------|
| `1`-`7` | Switch tab (Gmail, Chat, Calendar, Drive, Jira, Search, Dashboard) |
| `Tab` / `Shift+Tab` | Navigate between panels |
| `r` | Reload current tab (clears cache) |
| `?` | Help |
| `q` | Quit |

### Gmail

| Key | Action |
|-----|--------|
| `c` | Compose new email |
| `r` | Reply |
| `R` | Reply all |
| `f` | Forward |
| `d` | Move to trash |
| `e` | Archive |
| `m` | Toggle read/unread |
| `s` | Toggle star |
| `/` | Search inbox |
| `a` | Download attachment |
| `t` | View thread |
| `o` | Open in browser |
| `g` | Open Gmail web |

### Jira

| Key | Action |
|-----|--------|
| `c` | Create issue |
| `t` | Transition status |
| `w` | Log work |
| `C` | Add comment |
| `o` | Open in browser |
| `/` | JQL search |
| `F1`-`F9` | Saved JQL filters |

### Calendar

| Key | Action |
|-----|--------|
| `c` | Create event |
| `/` | Search |
| `o` | Open in browser |

### Drive

| Key | Action |
|-----|--------|
| `/` | Search files |
| `d` | Download file |
| `n` | New folder |
| `u` | Upload file |
| `o` | Open in browser |

### Chat

| Key | Action |
|-----|--------|
| `c` | Compose message |
| `/` | Search |

## Architecture

```
WorkspaceTUI (Textual App)
├── Tabs (UI layer)
│   ├── Gmail, Chat, Calendar, Drive, Jira, Search, Dashboard
│   └── Widgets (email list, issue detail, compose modal, ...)
├── Services (business logic)
│   ├── Gmail, Chat, Calendar, Drive, Jira, Search, Dashboard
│   └── BaseService (retry with exponential backoff, error categorization)
├── Auth
│   ├── Google OAuth2 (Desktop flow, token auto-refresh)
│   └── Jira Basic Auth (API token, per-account sessions)
├── Cache (diskcache, per-service TTL)
├── Notifications (plyer, OS-level desktop notifications)
├── Polling (PollManager, state-diffing, first-poll-silent)
└── Config (pydantic-settings, .env)
```

Services never import UI components. Tabs receive services via Textual's composition model.

## Testing

```bash
uv run pytest --cov --cov-report=term-missing
```

Lint and format checks:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

Coverage threshold is set to 85% in `pyproject.toml`. The test suite uses mocked API responses and runs without network access.

## Contributing

Contributions are welcome. Open an issue to discuss proposed changes before submitting a pull request. Follow the existing code style (enforced by ruff) and make sure tests pass with the coverage threshold.

## Security

For vulnerability reports, see [SECURITY.md](SECURITY.md).

## License

Released under the MIT License — see [LICENSE](LICENSE).

## Author

Andrea Bonacci — [@AndreaBonn](https://github.com/AndreaBonn)

---

If this project is useful to you, a star on GitHub is appreciated.
