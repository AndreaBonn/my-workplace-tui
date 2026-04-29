from dataclasses import dataclass as stdlib_dataclass
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: src/workspace_tui/config/settings.py → 3 levels up
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict. Handles comments, quotes, empty lines."""
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("'\"")
    return env


@stdlib_dataclass
class JiraAccountConfig:
    """Configuration for a single Jira account."""

    name: str
    base_url: str
    default_project: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google OAuth2
    google_client_secret_path: Path = _PROJECT_ROOT / "credentials" / "client_secret.json"
    google_token_path: Path = _PROJECT_ROOT / "credentials" / "token.json"

    # Gmail
    gmail_poll_interval: int = 60
    gmail_max_results: int = 50

    # Google Chat
    chat_poll_interval: int = 30

    # Google account (email) — forces Google links to open with this account
    google_account_email: str = ""

    # Google Calendar
    calendar_poll_interval: int = 300

    # Notifications
    notifications_enabled: bool = True

    # Google Drive
    workspace_domain: str = ""
    drive_download_dir: Path = Path("~/Scaricati")

    # Cache
    cache_enabled: bool = True
    cache_ttl: int = 300

    # Jira (optional)
    jira_username: str = ""
    jira_api_token: str = ""
    jira_base_url: str = ""
    jira_default_project: str = ""
    jira_account_id: str = ""
    jira_poll_interval: int = 120
    jira_max_results: int = 50
    jira_allow_http: bool = False

    # Multi-account: comma-separated account names (e.g. "linkalab,marzocco")
    jira_accounts: str = ""

    # Saved JQL filters (accessed via F1-F9)
    jira_saved_jql_1: str = ""
    jira_saved_jql_2: str = ""
    jira_saved_jql_3: str = ""
    jira_saved_jql_4: str = ""
    jira_saved_jql_5: str = ""
    jira_saved_jql_6: str = ""
    jira_saved_jql_7: str = ""
    jira_saved_jql_8: str = ""
    jira_saved_jql_9: str = ""

    @property
    def jira_configured(self) -> bool:
        return bool(
            self.jira_username
            and self.jira_api_token
            and (self.jira_base_url or self.jira_accounts)
        )

    @property
    def jira_account_configs(self) -> list[JiraAccountConfig]:
        """Build per-account configs from env vars.

        Multi-account mode (JIRA_ACCOUNTS set):
            Reads JIRA_{NAME}_BASE_URL and JIRA_{NAME}_DEFAULT_PROJECT
            for each account name.
        Single-account mode (legacy):
            Wraps flat JIRA_BASE_URL / JIRA_DEFAULT_PROJECT into one config.
        """
        if not self.jira_accounts:
            if self.jira_base_url:
                return [
                    JiraAccountConfig(
                        name="default",
                        base_url=self.jira_base_url,
                        default_project=self.jira_default_project,
                    )
                ]
            return []

        env_vars = {**_parse_env_file(_ENV_FILE), **dict(__import__("os").environ)}
        configs: list[JiraAccountConfig] = []
        for raw_name in self.jira_accounts.split(","):
            name = raw_name.strip()
            if not name:
                continue
            prefix = f"JIRA_{name.upper()}_"
            base_url = env_vars.get(f"{prefix}BASE_URL", "")
            default_project = env_vars.get(f"{prefix}DEFAULT_PROJECT", "")
            if base_url:
                configs.append(
                    JiraAccountConfig(
                        name=name,
                        base_url=base_url,
                        default_project=default_project,
                    )
                )
        return configs

    @property
    def jira_is_multi_account(self) -> bool:
        return len(self.jira_account_configs) > 1

    @property
    def saved_jql_filters(self) -> dict[int, str]:
        filters: dict[int, str] = {}
        for i in range(1, 10):
            value = getattr(self, f"jira_saved_jql_{i}")
            if value:
                filters[i] = value
        return filters

    @field_validator("drive_download_dir", mode="before")
    @classmethod
    def expand_download_dir(cls, v: str | Path) -> Path:
        return Path(str(v)).expanduser()

    @field_validator(
        "gmail_poll_interval",
        "chat_poll_interval",
        "calendar_poll_interval",
        "jira_poll_interval",
        mode="before",
    )
    @classmethod
    def validate_poll_interval(cls, v: int) -> int:
        v = int(v)
        if v < 10:
            return 10
        return v


def load_settings() -> Settings:
    return Settings()
