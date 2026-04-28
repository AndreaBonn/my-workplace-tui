import pytest

from workspace_tui.auth.jira_auth import create_jira_session
from workspace_tui.services.errors import ConfigurationError


class TestCreateJiraSession:
    def test_creates_session_with_valid_params(self):
        session = create_jira_session(
            username="user@test.com",
            api_token="test-token",
            base_url="https://test.atlassian.net",
        )
        assert "Authorization" in session.headers
        assert session.headers["Authorization"].startswith("Basic ")
        assert session.headers["Content-Type"] == "application/json"
        assert session.base_url == "https://test.atlassian.net"

    def test_strips_trailing_slash(self):
        session = create_jira_session(
            username="user@test.com",
            api_token="test-token",
            base_url="https://test.atlassian.net/",
        )
        assert session.base_url == "https://test.atlassian.net"

    def test_raises_on_empty_username(self):
        with pytest.raises(ConfigurationError):
            create_jira_session(
                username="",
                api_token="test-token",
                base_url="https://test.atlassian.net",
            )

    def test_raises_on_empty_token(self):
        with pytest.raises(ConfigurationError):
            create_jira_session(
                username="user@test.com",
                api_token="",
                base_url="https://test.atlassian.net",
            )

    def test_raises_on_empty_url(self):
        with pytest.raises(ConfigurationError):
            create_jira_session(
                username="user@test.com",
                api_token="test-token",
                base_url="",
            )

    def test_token_not_in_plain_text(self):
        session = create_jira_session(
            username="user@test.com",
            api_token="supersecret",
            base_url="https://test.atlassian.net",
        )
        auth_header = session.headers["Authorization"]
        assert "supersecret" not in auth_header

    def test_warns_on_non_https_url(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="workspace_tui.auth.jira_auth"):
            session = create_jira_session(
                username="user@test.com",
                api_token="test-token",
                base_url="http://test.atlassian.net",
            )
        assert session.base_url == "http://test.atlassian.net"
