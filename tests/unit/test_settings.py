from pathlib import Path

from workspace_tui.config.settings import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings()
        assert s.gmail_poll_interval == 60
        assert s.gmail_max_results == 50
        assert s.chat_poll_interval == 30
        assert s.calendar_poll_interval == 300
        assert s.notifications_enabled is True
        assert s.cache_enabled is True
        assert s.cache_ttl == 300

    def test_jira_not_configured_when_empty(self):
        s = Settings(jira_username="", jira_api_token="", jira_base_url="")
        assert s.jira_configured is False

    def test_jira_not_configured_when_partial(self):
        s = Settings(jira_username="user@test.com", jira_api_token="", jira_base_url="")
        assert s.jira_configured is False

    def test_jira_configured_when_all_set(self):
        s = Settings(
            jira_username="user@test.com",
            jira_api_token="token-123",
            jira_base_url="https://test.atlassian.net",
        )
        assert s.jira_configured is True

    def test_poll_interval_minimum_enforced(self):
        s = Settings(gmail_poll_interval=1, chat_poll_interval=5)
        assert s.gmail_poll_interval == 10
        assert s.chat_poll_interval == 10

    def test_poll_interval_valid_kept(self):
        s = Settings(gmail_poll_interval=120)
        assert s.gmail_poll_interval == 120

    def test_saved_jql_filters_empty_by_default(self):
        s = Settings()
        assert s.saved_jql_filters == {}

    def test_saved_jql_filters_populated(self):
        s = Settings(
            jira_saved_jql_1="assignee = currentUser()",
            jira_saved_jql_3="project = PROJ",
        )
        assert s.saved_jql_filters == {
            1: "assignee = currentUser()",
            3: "project = PROJ",
        }

    def test_google_paths_are_path_objects(self):
        s = Settings()
        assert isinstance(s.google_client_secret_path, Path)
        assert isinstance(s.google_token_path, Path)

    def test_drive_download_dir_expanded(self):
        s = Settings(drive_download_dir="~/Downloads")
        assert "~" not in str(s.drive_download_dir)


class TestJiraAccountConfigs:
    def test_single_account_backward_compat(self):
        s = Settings(
            jira_username="user@test.com",
            jira_api_token="token",
            jira_base_url="https://acme.atlassian.net",
            jira_default_project="ACME",
        )
        configs = s.jira_account_configs
        assert len(configs) == 1
        assert configs[0].name == "default"
        assert configs[0].base_url == "https://acme.atlassian.net"
        assert configs[0].default_project == "ACME"

    def test_no_accounts_when_unconfigured(self):
        s = Settings(jira_username="", jira_api_token="", jira_base_url="")
        assert s.jira_account_configs == []

    def test_multi_account_from_env_vars(self, monkeypatch):
        monkeypatch.setenv("JIRA_ALPHA_BASE_URL", "https://alpha.atlassian.net")
        monkeypatch.setenv("JIRA_ALPHA_DEFAULT_PROJECT", "AA")
        monkeypatch.setenv("JIRA_BETA_BASE_URL", "https://beta.atlassian.net")
        monkeypatch.setenv("JIRA_BETA_DEFAULT_PROJECT", "BB")

        s = Settings(
            jira_username="user@test.com",
            jira_api_token="token",
            jira_accounts="alpha,beta",
        )
        configs = s.jira_account_configs
        assert len(configs) == 2
        names = {c.name for c in configs}
        assert names == {"alpha", "beta"}

    def test_jira_configured_with_accounts(self):
        s = Settings(
            jira_username="user@test.com",
            jira_api_token="token",
            jira_accounts="alpha",
        )
        assert s.jira_configured is True

    def test_is_multi_account_false_for_single(self):
        s = Settings(
            jira_username="u",
            jira_api_token="t",
            jira_base_url="https://x.atlassian.net",
        )
        assert s.jira_is_multi_account is False

    def test_is_multi_account_true_for_two(self, monkeypatch):
        monkeypatch.setenv("JIRA_A_BASE_URL", "https://a.atlassian.net")
        monkeypatch.setenv("JIRA_B_BASE_URL", "https://b.atlassian.net")
        s = Settings(
            jira_username="u",
            jira_api_token="t",
            jira_accounts="a,b",
        )
        assert s.jira_is_multi_account is True

    def test_skips_accounts_without_base_url(self, monkeypatch):
        monkeypatch.setenv("JIRA_VALID_BASE_URL", "https://valid.atlassian.net")
        s = Settings(
            jira_username="u",
            jira_api_token="t",
            jira_accounts="valid,missing",
        )
        configs = s.jira_account_configs
        assert len(configs) == 1
        assert configs[0].name == "valid"


class TestLoadSettings:
    def test_returns_settings_instance(self):
        from workspace_tui.config.settings import load_settings

        s = load_settings()
        assert isinstance(s, Settings)
