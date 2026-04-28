import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from workspace_tui.auth.oauth import load_or_create_credentials
from workspace_tui.services.errors import ConfigurationError


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
