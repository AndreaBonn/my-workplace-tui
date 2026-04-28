import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from workspace_tui.auth.oauth import load_or_create_credentials, refresh_credentials
from workspace_tui.services.errors import AuthenticationError, ConfigurationError


class TestLoadOrCreateCredentials:
    def test_missing_client_secret_raises(self):
        with pytest.raises(ConfigurationError, match="non trovato"):
            load_or_create_credentials(
                client_secret_path=Path("/nonexistent/client_secret.json"),
                token_path=Path("/tmp/token.json"),
            )

    @patch("workspace_tui.auth.oauth.Credentials")
    def test_loads_existing_valid_token(self, mock_creds_class):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.expired = False
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as secret_file:
            json.dump({"installed": {}}, secret_file)
            secret_path = Path(secret_file.name)

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as token_file:
            json.dump({}, token_file)
            token_path = Path(token_file.name)

        result = load_or_create_credentials(
            client_secret_path=secret_path,
            token_path=token_path,
        )
        assert result == mock_creds

    @patch("workspace_tui.auth.oauth.InstalledAppFlow")
    @patch("workspace_tui.auth.oauth.Credentials")
    def test_runs_flow_when_no_token(self, mock_creds_class, mock_flow_class):
        mock_creds_class.from_authorized_user_file.side_effect = Exception("no token")

        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "test"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as secret_file:
            json.dump({"installed": {}}, secret_file)
            secret_path = Path(secret_file.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "token.json"
            result = load_or_create_credentials(
                client_secret_path=secret_path,
                token_path=token_path,
            )

        assert result == mock_creds
        mock_flow.run_local_server.assert_called_once_with(port=0)

    @patch("workspace_tui.auth.oauth._save_token")
    @patch("workspace_tui.auth.oauth.Request")
    @patch("workspace_tui.auth.oauth.Credentials")
    def test_refreshes_expired_token(self, mock_creds_class, mock_request, mock_save):
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as secret_file:
            json.dump({"installed": {}}, secret_file)
            secret_path = Path(secret_file.name)

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as token_file:
            json.dump({}, token_file)
            token_path = Path(token_file.name)

        result = load_or_create_credentials(
            client_secret_path=secret_path,
            token_path=token_path,
        )
        assert result == mock_creds
        mock_creds.refresh.assert_called_once()

    @patch("workspace_tui.auth.oauth.InstalledAppFlow")
    @patch("workspace_tui.auth.oauth.Request")
    @patch("workspace_tui.auth.oauth.Credentials")
    def test_refresh_failure_triggers_flow(self, mock_creds_class, mock_request, mock_flow_class):
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh-token"
        mock_creds.refresh.side_effect = Exception("refresh failed")
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        new_creds = MagicMock()
        new_creds.to_json.return_value = '{"token": "new"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = new_creds
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as secret_file:
            json.dump({"installed": {}}, secret_file)
            secret_path = Path(secret_file.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "token.json"
            result = load_or_create_credentials(
                client_secret_path=secret_path,
                token_path=token_path,
            )

        assert result == new_creds
        mock_flow.run_local_server.assert_called_once()

    @patch("workspace_tui.auth.oauth.InstalledAppFlow")
    @patch("workspace_tui.auth.oauth.Credentials")
    def test_flow_failure_raises_authentication_error(self, mock_creds_class, mock_flow_class):
        mock_creds_class.from_authorized_user_file.side_effect = Exception("no token")
        mock_flow_class.from_client_secrets_file.side_effect = Exception("flow broke")

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as secret_file:
            json.dump({"installed": {}}, secret_file)
            secret_path = Path(secret_file.name)

        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = Path(tmpdir) / "token.json"
            with pytest.raises(AuthenticationError, match="OAuth2 flow failed"):
                load_or_create_credentials(
                    client_secret_path=secret_path,
                    token_path=token_path,
                )


class TestRefreshCredentials:
    def test_refreshes_expired_creds(self):
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "token"

        with patch("workspace_tui.auth.oauth.Request"):
            result = refresh_credentials(mock_creds)

        assert result == mock_creds
        mock_creds.refresh.assert_called_once()

    def test_skips_refresh_when_not_expired(self):
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds.refresh_token = "token"

        result = refresh_credentials(mock_creds)
        assert result == mock_creds
        mock_creds.refresh.assert_not_called()

    def test_skips_refresh_when_no_refresh_token(self):
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = None

        result = refresh_credentials(mock_creds)
        assert result == mock_creds
        mock_creds.refresh.assert_not_called()
