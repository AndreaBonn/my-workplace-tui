**English** | [Italiano](SECURITY.it.md)

# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

Use [GitHub Security Advisories](https://github.com/AndreaBonn/my-workplace-tui/security/advisories/new) to report vulnerabilities privately.

Do not open public issues for security vulnerabilities.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Impact assessment (what an attacker could achieve)

### Response timeline

- Acknowledgment: within 72 hours
- Critical fixes: target 30 days from report
- Public disclosure: coordinated after the fix is released

## Security Measures Implemented

The following measures have been verified in the source code:

- **OAuth2 token file permissions**: tokens are stored with `0600` permissions, readable only by the file owner (`auth/oauth.py:95`)
- **HTTPS enforcement for Jira**: connections to Jira reject non-HTTPS URLs by default; cleartext is allowed only with explicit opt-in via `JIRA_ALLOW_HTTP=true` (`auth/jira_auth.py:46-55`)
- **No hardcoded secrets**: all credentials are loaded from `.env` via pydantic-settings (`config/settings.py`); `.env` and `credentials/` are excluded from version control (`.gitignore`)
- **Input validation**: polling intervals and file paths are validated at startup through Pydantic field validators (`config/settings.py:80-97`)
- **Dependency lockfile**: `uv.lock` pins all transitive dependency versions

## Security Best Practices for Users

- Store `credentials/client_secret.json` and `.env` outside of version control. The `.gitignore` already excludes them, but verify if you use a custom setup.
- The local cache (`~/.local/share/workspace-tui/cache/`) contains unencrypted API response data (email snippets, calendar events, Jira summaries). Protect it with appropriate filesystem permissions.
- OAuth2 scopes include write access (`gmail.modify`, `calendar`, `drive`). Review `auth/oauth.py:10-16` for the full scope list.
- Rotate Jira API tokens periodically via [Atlassian account settings](https://id.atlassian.com/manage-profile/security/api-tokens).

## Out of Scope

The following are not considered vulnerabilities for this project:

- Attacks requiring physical access to the machine
- Social engineering
- Self-XSS or attacks requiring the user to run arbitrary commands on their own terminal
- Vulnerabilities in third-party dependencies that are already publicly disclosed (report upstream instead)
- Issues requiring a compromised Google or Atlassian account

## Acknowledgments

No security vulnerabilities have been reported yet.

---

[Back to README](README.md)
