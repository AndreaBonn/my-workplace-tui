# Security Policy

## Credential handling

- **OAuth2 tokens** are stored locally at `credentials/token.json` with `0600` permissions. They are never committed to git (`.gitignore`).
- **Jira API tokens** are read from `.env` (also in `.gitignore`). HTTPS is enforced for Jira connections.
- **`client_secret.json`** (OAuth2 client credentials) must be obtained from Google Cloud Console and placed manually in `credentials/`. It is excluded from version control.

## Local cache

Workspace TUI uses `diskcache` to cache API responses locally at `~/.local/share/workspace-tui/cache/`. Cached data may include email snippets, calendar events, and Jira issue summaries. The cache is not encrypted — it relies on filesystem permissions.

## OAuth2 scopes

The application requests write-level OAuth2 scopes (`gmail.modify`, `calendar`, `drive`). See `ASSUMPTIONS.md` for the rationale behind this decision.

## Reporting a vulnerability

If you discover a security issue, please open a private issue or contact the maintainer directly. Do not file public issues for security vulnerabilities.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |
