from unittest.mock import patch

from workspace_tui.utils.url_utils import _add_authuser, _is_google_url, open_google_url


class TestIsGoogleUrl:
    def test_google_com_subdomain(self):
        assert _is_google_url("https://docs.google.com/document/d/123") is True

    def test_meet_google_com(self):
        assert _is_google_url("https://meet.google.com/abc-def") is True

    def test_non_google_url(self):
        assert _is_google_url("https://example.com/page") is False

    def test_empty_url(self):
        assert _is_google_url("") is False

    def test_malformed_url(self):
        assert _is_google_url("not-a-url") is False


class TestAddAuthuser:
    def test_adds_authuser_param(self):
        url = _add_authuser("https://docs.google.com/doc", "user@example.com")
        assert "authuser=user%40example.com" in url

    def test_preserves_existing_params(self):
        url = _add_authuser("https://docs.google.com/doc?foo=bar", "user@example.com")
        assert "foo=bar" in url
        assert "authuser=" in url

    def test_replaces_existing_authuser(self):
        url = _add_authuser("https://docs.google.com/doc?authuser=old@test.com", "new@test.com")
        assert "new%40test.com" in url
        assert url.count("authuser=") == 1


class TestOpenGoogleUrl:
    @patch("workspace_tui.utils.url_utils.webbrowser.open")
    def test_opens_google_url_with_authuser(self, mock_open):
        open_google_url("https://docs.google.com/doc", google_account_email="user@test.com")
        called_url = mock_open.call_args[0][0]
        assert "authuser=" in called_url

    @patch("workspace_tui.utils.url_utils.webbrowser.open")
    def test_opens_non_google_url_unchanged(self, mock_open):
        open_google_url("https://example.com", google_account_email="user@test.com")
        mock_open.assert_called_once_with("https://example.com")

    @patch("workspace_tui.utils.url_utils.webbrowser.open")
    def test_opens_without_email(self, mock_open):
        open_google_url("https://docs.google.com/doc")
        mock_open.assert_called_once_with("https://docs.google.com/doc")
