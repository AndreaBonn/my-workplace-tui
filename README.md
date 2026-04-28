**English** | [Italiano](README.it.md)

# Workspace TUI

Terminal interface for Gmail, Google Chat, Google Calendar, Google Drive, and Jira.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/my-workplace-tui/actions/workflows/ci.yml)

Workspace TUI is a keyboard-driven terminal application that provides unified access to Google Workspace services and Jira without leaving the terminal. It replaces browser tabs with a single tabbed interface for daily operations on email, chat, calendar, files, and issue tracking.

## Features

- Gmail: read inbox, preview messages, compose emails
- Google Chat: browse spaces and messages
- Google Calendar: view upcoming events, create new events
- Google Drive: navigate files, download, distinguish internal vs external shares
- Jira: list/create/detail issues, log work, saved JQL filters (F1-F9)
- Background polling with OS desktop notifications (Linux)
- Local response cache via diskcache
- Tab switching with number keys (1-5), keyboard shortcuts throughout

## Installation

Requirements: Python 3.11+, a terminal with at least 120x30 characters and 256-color support. Linux (Ubuntu 22.04+ tested).

```bash
git clone https://github.com/AndreaBonn/my-workplace-tui.git
cd my-workplace-tui
./install.sh
```

The install script:
1. Verifies Python 3.11+
2. Installs [uv](https://docs.astral.sh/uv/) if not present (interactive prompt)
3. Installs dependencies via `uv sync`
4. Creates `.env` from `.env.example`
5. Creates the `workspace-tui` launcher in `~/.local/bin/`

## Usage

```bash
workspace-tui
```

Or from the project directory:

```bash
uv run python -m workspace_tui
```

### Google Cloud setup (one-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable APIs: Gmail, Google Chat, Google Calendar, Google Drive
3. Create OAuth2 credentials (Desktop application type)
4. Download the JSON file and save it as `credentials/client_secret.json`
5. On first launch, the browser opens for OAuth2 authorization — the token is saved automatically

### Jira setup (optional)

1. Generate an API token at [Atlassian account settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Fill the Jira variables in `.env` (see Configuration below)

If Jira is not configured, the Jira tab is disabled. All other tabs work normally.

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| 1-5 | Switch tab (Gmail, Chat, Calendar, Drive, Jira) |
| r | Reload current tab |
| ? | Help |
| q | Quit |

## Configuration

All settings are in `.env` (created from `.env.example` during installation). Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLIENT_SECRET_PATH` | Path to OAuth2 client secret | `credentials/client_secret.json` |
| `GMAIL_POLL_INTERVAL` | Gmail polling interval (seconds) | `60` |
| `CHAT_POLL_INTERVAL` | Chat polling interval (seconds) | `30` |
| `CALENDAR_POLL_INTERVAL` | Calendar polling interval (seconds) | `300` |
| `NOTIFICATIONS_ENABLED` | Desktop notifications on/off | `true` |
| `CACHE_ENABLED` | Local cache on/off | `true` |
| `CACHE_TTL` | Cache TTL (seconds) | `300` |
| `JIRA_USERNAME` | Atlassian email | — |
| `JIRA_API_TOKEN` | Jira API token | — |
| `JIRA_BASE_URL` | Jira instance URL (HTTPS required) | — |
| `JIRA_DEFAULT_PROJECT` | Default project key | — |
| `DRIVE_DOWNLOAD_DIR` | Download directory for Drive files | `~/Scaricati` |
| `WORKSPACE_DOMAIN` | Google Workspace domain (for share filtering) | — |

See `.env.example` for the full list including saved JQL filters.

## Testing

```bash
uv run pytest --cov --cov-report=term-missing
```

Lint and format checks:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

## Contributing

Contributions are welcome. Open an issue to discuss proposed changes before submitting a pull request. Follow the existing code style (enforced by ruff) and ensure tests pass with the coverage threshold (85%).

## Security

For vulnerability reports, see [SECURITY.md](SECURITY.md).

## License

Released under the MIT License — see [LICENSE](LICENSE).

## Author

Andrea Bonacci — [@AndreaBonn](https://github.com/AndreaBonn)

---

If this project is useful to you, a star on GitHub is appreciated.
