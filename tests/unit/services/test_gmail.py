import base64
from unittest.mock import MagicMock, patch

import pytest

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.gmail import (
    GmailService,
)


@pytest.fixture
def cache():
    return CacheManager(enabled=False)


@pytest.fixture
def mock_gmail_api():
    return MagicMock()


@pytest.fixture
def gmail_service(mock_gmail_api, cache):
    with patch("workspace_tui.services.gmail.build", return_value=mock_gmail_api):
        service = GmailService(credentials=MagicMock(), cache=cache)
    service._service = mock_gmail_api
    return service


def _make_message_response(
    msg_id: str = "msg1",
    subject: str = "Test Subject",
    from_addr: str = "sender@test.com",
    label_ids: list[str] | None = None,
    body_text: str = "Hello",
    fmt: str = "full",
) -> dict:
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode()
    response = {
        "id": msg_id,
        "threadId": "thread1",
        "labelIds": label_ids or ["INBOX", "UNREAD"],
        "snippet": body_text[:50],
        "payload": {
            "headers": [
                {"name": "From", "value": from_addr},
                {"name": "To", "value": "me@test.com"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Mon, 28 Apr 2026 14:30:00 +0000"},
            ],
            "mimeType": "text/plain",
            "body": {"data": encoded_body} if fmt == "full" else {},
        },
    }
    return response


class TestListLabels:
    def test_returns_labels(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX", "type": "system"},
                {"id": "Label_1", "name": "Lavoro", "type": "user"},
            ]
        }
        mock_gmail_api.users().labels().get().execute.return_value = {
            "messagesUnread": 5,
            "messagesTotal": 100,
        }

        labels = gmail_service.list_labels()
        assert len(labels) == 2
        assert labels[0].name == "In arrivo"
        assert labels[0].unread_count == 5


class TestListMessages:
    def test_returns_messages_and_token(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}],
            "nextPageToken": "token123",
        }
        mock_gmail_api.users().messages().get().execute.return_value = _make_message_response(
            fmt="metadata"
        )

        messages, next_token = gmail_service.list_messages(label_id="INBOX")
        assert len(messages) == 2
        assert next_token == "token123"

    def test_empty_inbox(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().list().execute.return_value = {}
        messages, next_token = gmail_service.list_messages()
        assert messages == []
        assert next_token is None


class TestGetMessage:
    def test_parses_full_message(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().get().execute.return_value = _make_message_response(
            msg_id="msg1", subject="Test", body_text="Hello world"
        )

        msg = gmail_service.get_message("msg1")
        assert msg is not None
        assert msg.header.subject == "Test"
        assert msg.body_text == "Hello world"
        assert msg.is_unread is True


class TestSendMessage:
    def test_sends_and_invalidates_cache(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().send().execute.return_value = {"id": "sent1"}

        result = gmail_service.send_message(
            to="recipient@test.com",
            subject="Test",
            body="Hello",
        )
        assert result == "sent1"

    def test_sends_with_cc_and_thread(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().send().execute.return_value = {"id": "sent2"}

        result = gmail_service.send_message(
            to="recipient@test.com",
            subject="Re: Test",
            body="Reply",
            cc="cc@test.com",
            thread_id="thread1",
        )
        assert result == "sent2"


class TestCreateDraft:
    def test_creates_draft(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().drafts().create().execute.return_value = {"id": "draft1"}

        result = gmail_service.create_draft(
            to="recipient@test.com",
            subject="Draft",
            body="Draft body",
        )
        assert result == "draft1"


class TestTrashMessage:
    def test_trashes_message(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().trash().execute.return_value = {}
        gmail_service.trash_message("msg1")


class TestModifyMessage:
    def test_adds_labels(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.modify_message("msg1", add_labels=["STARRED"])

    def test_removes_labels(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.modify_message("msg1", remove_labels=["UNREAD"])


class TestToggleRead:
    def test_mark_as_read(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.toggle_read("msg1", is_unread=True)

    def test_mark_as_unread(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.toggle_read("msg1", is_unread=False)


class TestGetAttachment:
    def test_decodes_attachment_data(self, gmail_service, mock_gmail_api):
        raw_data = base64.urlsafe_b64encode(b"file content").decode()
        mock_gmail_api.users().messages().attachments().get().execute.return_value = {
            "data": raw_data
        }
        result = gmail_service.get_attachment("msg1", "att1")
        assert result == b"file content"


class TestToggleStar:
    def test_unstar_message(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.toggle_star("msg1", is_starred=True)

    def test_star_message(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.toggle_star("msg1", is_starred=False)


class TestArchiveMessage:
    def test_archives_by_removing_inbox_label(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().modify().execute.return_value = {}
        gmail_service.archive_message("msg1")


class TestGetThreadMessages:
    def test_returns_thread_messages(self, gmail_service, mock_gmail_api):
        msg_data = _make_message_response(msg_id="msg1", body_text="Thread msg 1")
        mock_gmail_api.users().threads().get().execute.return_value = {"messages": [msg_data]}
        messages = gmail_service.get_thread_messages("thread1")
        assert len(messages) == 1
        assert messages[0].body_text == "Thread msg 1"

    def test_handles_parse_error_gracefully(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().threads().get().execute.return_value = {
            "messages": [{"malformed": True}]
        }
        messages = gmail_service.get_thread_messages("thread1")
        assert messages == []


class TestDownloadAttachment:
    def test_saves_attachment_to_disk(self, gmail_service, mock_gmail_api, tmp_path):
        from workspace_tui.services.gmail import EmailAttachment

        raw_data = base64.urlsafe_b64encode(b"attachment data").decode()
        mock_gmail_api.users().messages().attachments().get().execute.return_value = {
            "data": raw_data
        }

        attachment = EmailAttachment(
            attachment_id="att1",
            filename="report.pdf",
            mime_type="application/pdf",
            size=100,
        )
        path = gmail_service.download_attachment("msg1", attachment, tmp_path)
        assert path.exists()
        assert path.read_bytes() == b"attachment data"
        assert path.name == "report.pdf"


class TestSendMessageWithReply:
    def test_sends_reply_with_reply_to_id(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().messages().send().execute.return_value = {"id": "reply1"}
        result = gmail_service.send_message(
            to="recipient@test.com",
            subject="Re: Test",
            body="My reply",
            reply_to_id="<original-msg-id@mail.com>",
            thread_id="thread1",
        )
        assert result == "reply1"


class TestCreateDraftWithCc:
    def test_creates_draft_with_cc(self, gmail_service, mock_gmail_api):
        mock_gmail_api.users().drafts().create().execute.return_value = {"id": "draft2"}
        result = gmail_service.create_draft(
            to="recipient@test.com",
            subject="Draft with CC",
            body="Body",
            cc="cc@test.com",
        )
        assert result == "draft2"


class TestParseMessage:
    def test_multipart_message(self, gmail_service):
        html_body = base64.urlsafe_b64encode(b"<p>Hello</p>").decode()
        text_body = base64.urlsafe_b64encode(b"Hello").decode()
        data = {
            "id": "msg1",
            "threadId": "thread1",
            "labelIds": ["INBOX"],
            "snippet": "Hello",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@test.com"},
                    {"name": "Subject", "value": "Test"},
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": text_body}},
                    {"mimeType": "text/html", "body": {"data": html_body}},
                ],
            },
        }
        msg = gmail_service._parse_message(data, include_body=True)
        assert msg.body_text == "Hello"
        assert msg.body_html == "<p>Hello</p>"

    def test_message_with_attachment(self, gmail_service):
        data = {
            "id": "msg1",
            "threadId": "thread1",
            "labelIds": [],
            "snippet": "",
            "payload": {
                "headers": [{"name": "Subject", "value": "With attachment"}],
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {
                            "data": base64.urlsafe_b64encode(b"text").decode(),
                        },
                    },
                    {
                        "mimeType": "application/pdf",
                        "filename": "report.pdf",
                        "body": {"attachmentId": "att123", "size": 1024},
                    },
                ],
            },
        }
        msg = gmail_service._parse_message(data, include_body=True)
        assert len(msg.attachments) == 1
        assert msg.attachments[0].filename == "report.pdf"
        assert msg.attachments[0].size == 1024
