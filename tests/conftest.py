import pytest

from workspace_tui.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        google_client_secret_path="credentials/client_secret.json",
        google_token_path="credentials/token.json",
        jira_username="",
        jira_api_token="",
        jira_base_url="",
    )


@pytest.fixture
def jira_settings() -> Settings:
    return Settings(
        google_client_secret_path="credentials/client_secret.json",
        google_token_path="credentials/token.json",
        jira_username="test@example.com",
        jira_api_token="test-token",
        jira_base_url="https://test.atlassian.net",
        jira_default_project="TEST",
    )
