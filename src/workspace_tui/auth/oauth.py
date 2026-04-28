from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from loguru import logger

from workspace_tui.services.errors import AuthenticationError, ConfigurationError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/chat.messages",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
]


def load_or_create_credentials(
    client_secret_path: Path,
    token_path: Path,
) -> Credentials:
    """Load existing credentials or initiate OAuth2 flow.

    Parameters
    ----------
    client_secret_path : Path
        Path to the OAuth2 client secret JSON file from Google Cloud Console.
    token_path : Path
        Path where the OAuth2 token will be saved/loaded.

    Returns
    -------
    Credentials
        Valid Google OAuth2 credentials.

    Raises
    ------
    ConfigurationError
        If client_secret.json is missing.
    AuthenticationError
        If the OAuth2 flow fails.
    """
    if not client_secret_path.exists():
        raise ConfigurationError(
            f"File {client_secret_path} non trovato. "
            "Scaricalo da Google Cloud Console e posizionalo nella cartella credentials/."
        )

    creds: Credentials | None = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes=SCOPES)
            logger.debug("Token loaded from {}", token_path)
        except Exception as exc:
            logger.warning("Failed to load token: {}", exc)
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, token_path)
            logger.info("Token refreshed successfully")
            return creds
        except Exception as exc:
            logger.warning("Token refresh failed: {}", exc)
            creds = None

    if creds and creds.valid:
        return creds

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret_path),
            scopes=SCOPES,
        )
        creds = flow.run_local_server(port=0)
        _save_token(creds, token_path)
        logger.info("OAuth2 flow completed, token saved")
        return creds
    except Exception as exc:
        raise AuthenticationError(f"OAuth2 flow failed: {exc}") from exc


def refresh_credentials(creds: Credentials) -> Credentials:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _save_token(creds: Credentials, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    logger.debug("Token saved to {}", token_path)
