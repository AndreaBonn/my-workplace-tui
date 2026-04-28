import base64
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.discovery import build
from loguru import logger

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.base import BaseService

CACHE_PREFIX = "gmail:"
TTL_MESSAGE_LIST = 60
TTL_MESSAGE_DETAIL = 600
TTL_LABELS = 300


@dataclass
class EmailAttachment:
    attachment_id: str
    filename: str
    mime_type: str
    size: int


@dataclass
class EmailHeader:
    from_address: str = ""
    to_address: str = ""
    cc_address: str = ""
    subject: str = ""
    date: str = ""


@dataclass
class EmailMessage:
    message_id: str
    thread_id: str
    header: EmailHeader
    snippet: str = ""
    body_html: str = ""
    body_text: str = ""
    label_ids: list[str] = field(default_factory=list)
    is_unread: bool = False
    is_starred: bool = False
    attachments: list[EmailAttachment] = field(default_factory=list)


@dataclass
class GmailLabel:
    label_id: str
    name: str
    label_type: str
    unread_count: int = 0
    total_count: int = 0


class GmailService(BaseService):
    SYSTEM_LABELS = {
        "INBOX": "In arrivo",
        "SENT": "Inviati",
        "DRAFT": "Bozze",
        "SPAM": "Spam",
        "TRASH": "Cestino",
        "STARRED": "Speciali",
        "IMPORTANT": "Importanti",
    }

    def __init__(self, credentials, cache: CacheManager) -> None:
        super().__init__(cache=cache)
        self._service = build("gmail", "v1", credentials=credentials)
        self._credentials = credentials

    def list_labels(self) -> list[GmailLabel]:
        def fetch():
            results = self._retry(
                lambda: self._service.users().labels().list(userId="me").execute()
            )
            labels = []
            for label_data in results.get("labels", []):
                label_id = label_data["id"]
                name = self.SYSTEM_LABELS.get(label_id, label_data.get("name", label_id))
                label_type = label_data.get("type", "user")

                detail = self._retry(
                    lambda lid=label_id: (
                        self._service.users().labels().get(userId="me", id=lid).execute()
                    )
                )
                unread = detail.get("messagesUnread", 0)
                total = detail.get("messagesTotal", 0)

                labels.append(
                    GmailLabel(
                        label_id=label_id,
                        name=name,
                        label_type=label_type,
                        unread_count=unread,
                        total_count=total,
                    )
                )
            return labels

        return self._cached(f"{CACHE_PREFIX}labels", ttl=TTL_LABELS, fetch=fetch)

    def list_messages(
        self,
        label_id: str = "INBOX",
        max_results: int = 50,
        query: str = "",
        page_token: str | None = None,
    ) -> tuple[list[EmailMessage], str | None]:
        """List messages for a label, returns (messages, next_page_token)."""
        cache_key = f"{CACHE_PREFIX}list:{label_id}:{query}:{page_token}"

        def fetch():
            params = {
                "userId": "me",
                "labelIds": [label_id] if label_id else None,
                "maxResults": max_results,
                "q": query or None,
            }
            if page_token:
                params["pageToken"] = page_token
            params = {k: v for k, v in params.items() if v is not None}

            results = self._retry(lambda: self._service.users().messages().list(**params).execute())

            messages = []
            for msg_data in results.get("messages", []):
                msg = self._get_message_summary(msg_data["id"])
                if msg:
                    messages.append(msg)

            next_token = results.get("nextPageToken")
            return messages, next_token

        return self._cached(cache_key, ttl=TTL_MESSAGE_LIST, fetch=fetch)

    def get_message(self, message_id: str) -> EmailMessage | None:
        cache_key = f"{CACHE_PREFIX}msg:{message_id}"

        def fetch():
            result = self._retry(
                lambda: (
                    self._service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )
            )
            return self._parse_message(result, include_body=True)

        return self._cached(cache_key, ttl=TTL_MESSAGE_DETAIL, fetch=fetch)

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        reply_to_id: str | None = None,
        thread_id: str | None = None,
    ) -> str:
        msg = MIMEMultipart()
        msg["to"] = to
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc
        if reply_to_id:
            msg["In-Reply-To"] = reply_to_id
            msg["References"] = reply_to_id
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        send_body: dict = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        result = self._retry(
            lambda: self._service.users().messages().send(userId="me", body=send_body).execute()
        )

        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("Email sent to {}", to)
        return result["id"]

    def create_draft(self, to: str, subject: str, body: str, cc: str = "") -> str:
        msg = MIMEMultipart()
        msg["to"] = to
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        draft_body = {"message": {"raw": raw}}

        result = self._retry(
            lambda: self._service.users().drafts().create(userId="me", body=draft_body).execute()
        )

        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("Draft created")
        return result["id"]

    def trash_message(self, message_id: str) -> None:
        self._retry(
            lambda: self._service.users().messages().trash(userId="me", id=message_id).execute()
        )
        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("Message {} trashed", message_id)

    def modify_message(
        self,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> None:
        body: dict = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels

        self._retry(
            lambda: (
                self._service.users()
                .messages()
                .modify(userId="me", id=message_id, body=body)
                .execute()
            )
        )
        self._cache.invalidate(f"{CACHE_PREFIX}msg:{message_id}")
        self._cache.invalidate_prefix(f"{CACHE_PREFIX}list:")

    def toggle_read(self, message_id: str, is_unread: bool) -> None:
        if is_unread:
            self.modify_message(message_id, remove_labels=["UNREAD"])
        else:
            self.modify_message(message_id, add_labels=["UNREAD"])

    def toggle_star(self, message_id: str, is_starred: bool) -> None:
        if is_starred:
            self.modify_message(message_id, remove_labels=["STARRED"])
        else:
            self.modify_message(message_id, add_labels=["STARRED"])

    def archive_message(self, message_id: str) -> None:
        self.modify_message(message_id, remove_labels=["INBOX"])

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        result = self._retry(
            lambda: (
                self._service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
        )
        data = result.get("data", "")
        return base64.urlsafe_b64decode(data)

    def download_attachment(
        self, message_id: str, attachment: EmailAttachment, dest_dir: Path
    ) -> Path:
        data = self.get_attachment(message_id, attachment.attachment_id)
        safe_name = Path(attachment.filename).name
        dest_path = dest_dir / safe_name
        dest_path.write_bytes(data)
        logger.info("Attachment saved to {}", dest_path)
        return dest_path

    def _get_message_summary(self, message_id: str) -> EmailMessage | None:
        try:
            result = self._retry(
                lambda: (
                    self._service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="metadata",
                        metadataHeaders=["From", "To", "Subject", "Date"],
                    )
                    .execute()
                )
            )
            return self._parse_message(result, include_body=False)
        except Exception as exc:
            logger.warning("Failed to fetch message {}: {}", message_id, exc)
            return None

    def _parse_message(self, data: dict, *, include_body: bool) -> EmailMessage:
        headers = {}
        payload = data.get("payload", {})
        for h in payload.get("headers", []):
            headers[h["name"].lower()] = h["value"]

        header = EmailHeader(
            from_address=headers.get("from", ""),
            to_address=headers.get("to", ""),
            cc_address=headers.get("cc", ""),
            subject=headers.get("subject", "(senza oggetto)"),
            date=headers.get("date", ""),
        )

        label_ids = data.get("labelIds", [])
        is_unread = "UNREAD" in label_ids
        is_starred = "STARRED" in label_ids

        body_html = ""
        body_text = ""
        attachments: list[EmailAttachment] = []

        if include_body:
            body_html, body_text, attachments = self._extract_body(payload)

        return EmailMessage(
            message_id=data["id"],
            thread_id=data.get("threadId", ""),
            header=header,
            snippet=data.get("snippet", ""),
            body_html=body_html,
            body_text=body_text,
            label_ids=label_ids,
            is_unread=is_unread,
            is_starred=is_starred,
            attachments=attachments,
        )

    def _extract_body(self, payload: dict) -> tuple[str, str, list[EmailAttachment]]:
        body_html = ""
        body_text = ""
        attachments: list[EmailAttachment] = []

        if payload.get("mimeType", "").startswith("multipart"):
            for part in payload.get("parts", []):
                h, t, a = self._extract_body(part)
                if h:
                    body_html = h
                if t:
                    body_text = t
                attachments.extend(a)
        else:
            mime = payload.get("mimeType", "")
            body_data = payload.get("body", {})

            if body_data.get("attachmentId"):
                attachments.append(
                    EmailAttachment(
                        attachment_id=body_data["attachmentId"],
                        filename=payload.get("filename", "attachment"),
                        mime_type=mime,
                        size=body_data.get("size", 0),
                    )
                )
            elif body_data.get("data"):
                decoded = base64.urlsafe_b64decode(body_data["data"]).decode(
                    "utf-8", errors="replace"
                )
                if mime == "text/html":
                    body_html = decoded
                elif mime == "text/plain":
                    body_text = decoded

        return body_html, body_text, attachments
