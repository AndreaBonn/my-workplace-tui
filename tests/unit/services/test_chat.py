from unittest.mock import MagicMock, patch

import pytest

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.chat import ChatService


@pytest.fixture
def cache():
    return CacheManager(enabled=False)


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.fixture
def chat_service(mock_api, cache):
    with patch("workspace_tui.services.chat.build", return_value=mock_api):
        service = ChatService(credentials=MagicMock(), cache=cache)
    service._service = mock_api
    return service


class TestListSpaces:
    def test_returns_spaces(self, chat_service, mock_api):
        mock_api.spaces().list().execute.return_value = {
            "spaces": [
                {"name": "spaces/abc", "displayName": "Mario Rossi", "spaceType": "DIRECT_MESSAGE"},
                {"name": "spaces/def", "displayName": "Team Dev", "spaceType": "SPACE"},
            ]
        }
        spaces = chat_service.list_spaces()
        assert len(spaces) == 2
        assert spaces[0].is_dm is True
        assert spaces[1].is_dm is False

    def test_empty_spaces(self, chat_service, mock_api):
        mock_api.spaces().list().execute.return_value = {"spaces": []}
        spaces = chat_service.list_spaces()
        assert spaces == []


class TestListMessages:
    def test_returns_messages(self, chat_service, mock_api):
        mock_api.spaces().messages().list().execute.return_value = {
            "messages": [
                {
                    "name": "spaces/abc/messages/1",
                    "sender": {"name": "users/123", "displayName": "Mario Rossi"},
                    "text": "Ciao!",
                    "createTime": "2026-04-28T14:30:00Z",
                },
            ]
        }
        messages = chat_service.list_messages("spaces/abc")
        assert len(messages) == 1
        assert messages[0].text == "Ciao!"
        assert messages[0].sender_display_name == "Mario Rossi"


class TestSendMessage:
    def test_sends_message(self, chat_service, mock_api):
        mock_api.spaces().messages().create().execute.return_value = {
            "name": "spaces/abc/messages/2"
        }
        result = chat_service.send_message(space_name="spaces/abc", text="Test message")
        assert result == "spaces/abc/messages/2"
