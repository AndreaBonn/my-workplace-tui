from dataclasses import dataclass

from googleapiclient.discovery import build
from loguru import logger

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.base import BaseService

CACHE_PREFIX = "chat:"
TTL_SPACES = 300
TTL_MESSAGES = 30


@dataclass
class ChatSpace:
    name: str
    display_name: str
    space_type: str
    is_dm: bool = False


@dataclass
class ChatMessage:
    name: str
    sender_name: str
    sender_display_name: str
    text: str
    create_time: str


class ChatService(BaseService):
    def __init__(self, credentials, cache: CacheManager) -> None:
        super().__init__(cache=cache)
        self._service = build("chat", "v1", credentials=credentials)
        self._credentials = credentials

    def list_spaces(self) -> list[ChatSpace]:
        def fetch():
            result = self._retry(lambda: self._service.spaces().list().execute())
            spaces = []
            for space in result.get("spaces", []):
                space_type = space.get("spaceType", space.get("type", ""))
                spaces.append(
                    ChatSpace(
                        name=space.get("name", ""),
                        display_name=space.get("displayName", "DM"),
                        space_type=space_type,
                        is_dm=space_type in ("DIRECT_MESSAGE", "GROUP_CHAT"),
                    )
                )
            return spaces

        return self._cached(f"{CACHE_PREFIX}spaces", ttl=TTL_SPACES, fetch=fetch)

    def list_messages(self, space_name: str, max_results: int = 50) -> list[ChatMessage]:
        cache_key = f"{CACHE_PREFIX}messages:{space_name}"

        def fetch():
            result = self._retry(
                lambda: (
                    self._service.spaces()
                    .messages()
                    .list(parent=space_name, pageSize=max_results)
                    .execute()
                )
            )
            messages = []
            for msg in result.get("messages", []):
                sender = msg.get("sender", {})
                messages.append(
                    ChatMessage(
                        name=msg.get("name", ""),
                        sender_name=sender.get("name", ""),
                        sender_display_name=sender.get("displayName", ""),
                        text=msg.get("text", ""),
                        create_time=msg.get("createTime", ""),
                    )
                )
            return messages

        return self._cached(cache_key, ttl=TTL_MESSAGES, fetch=fetch)

    def send_message(self, space_name: str, text: str) -> str:
        result = self._retry(
            lambda: (
                self._service.spaces()
                .messages()
                .create(parent=space_name, body={"text": text})
                .execute()
            )
        )
        self._cache.invalidate(f"{CACHE_PREFIX}messages:{space_name}")
        logger.info("Message sent to {}", space_name)
        return result.get("name", "")
