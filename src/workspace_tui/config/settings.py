from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google OAuth2
    google_client_secret_path: Path = Path("credentials/client_secret.json")
    google_token_path: Path = Path("credentials/token.json")

    # Gmail
    gmail_poll_interval: int = 60
    gmail_max_results: int = 50

    # Google Chat
    chat_poll_interval: int = 30

    # Google Calendar
    calendar_poll_interval: int = 300

    # Notifications
    notifications_enabled: bool = True

    # Google Drive
    workspace_domain: str = ""

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
        return bool(self.jira_username and self.jira_api_token and self.jira_base_url)

    @property
    def saved_jql_filters(self) -> dict[int, str]:
        filters: dict[int, str] = {}
        for i in range(1, 10):
            value = getattr(self, f"jira_saved_jql_{i}")
            if value:
                filters[i] = value
        return filters

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
