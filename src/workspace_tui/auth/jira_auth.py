from base64 import b64encode

import requests
from loguru import logger

from workspace_tui.services.errors import ConfigurationError


def create_jira_session(
    username: str,
    api_token: str,
    base_url: str,
    *,
    allow_http: bool = False,
) -> requests.Session:
    """Create a pre-configured requests.Session for Jira API.

    Parameters
    ----------
    username : str
        Jira username (Atlassian account email).
    api_token : str
        API token generated at id.atlassian.com.
    base_url : str
        Base URL of the Jira instance (e.g., https://company.atlassian.net).
    allow_http : bool
        If True, allow non-HTTPS URLs (for local development only).

    Returns
    -------
    requests.Session
        Session with Authorization, Content-Type, and Accept headers set.

    Raises
    ------
    ConfigurationError
        If any required parameter is empty or if the URL is not HTTPS
        (unless allow_http is True).
    """
    if not all([username, api_token, base_url]):
        raise ConfigurationError(
            "Configura JIRA_USERNAME, JIRA_API_TOKEN e JIRA_BASE_URL nel file .env"
        )

    base_url = base_url.rstrip("/")
    if not base_url.startswith("https://"):
        if allow_http:
            logger.warning(
                "Jira base URL does not use HTTPS — credentials transmitted in cleartext"
            )
        else:
            raise ConfigurationError(
                f"Jira base URL must use HTTPS (got: {base_url}). "
                "Set JIRA_ALLOW_HTTP=true in .env to override for local development."
            )

    token = b64encode(f"{username}:{api_token}".encode()).decode()

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    session.base_url = base_url  # type: ignore[attr-defined]

    logger.debug("Jira session created for {}", base_url)
    return session
