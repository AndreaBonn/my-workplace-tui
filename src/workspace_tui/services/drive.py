from dataclasses import dataclass
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from loguru import logger

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.base import BaseService

CACHE_PREFIX = "drive:"
TTL_FILE_LIST = 120
TTL_FILE_DETAIL = 300

EXPORT_FORMATS = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}

MIME_ICONS = {
    "application/vnd.google-apps.folder": "📁",
    "application/vnd.google-apps.document": "📄",
    "application/vnd.google-apps.spreadsheet": "📊",
    "application/vnd.google-apps.presentation": "📑",
    "application/pdf": "📕",
    "image/": "🖼",
}


@dataclass
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    size: int = 0
    modified_time: str = ""
    owner: str = ""
    is_folder: bool = False
    icon: str = "📄"


class DriveService(BaseService):
    def __init__(self, credentials, cache: CacheManager) -> None:
        super().__init__(cache=cache)
        self._service = build("drive", "v3", credentials=credentials)
        self._credentials = credentials

    def list_files(
        self,
        folder_id: str = "root",
        query: str = "",
        max_results: int = 100,
        page_token: str | None = None,
    ) -> tuple[list[DriveFile], str | None]:
        cache_key = f"{CACHE_PREFIX}list:{folder_id}:{query}:{page_token}"

        def fetch():
            q_parts = []
            if folder_id and not query:
                q_parts.append(f"'{folder_id}' in parents")
            q_parts.append("trashed = false")
            if query:
                sanitized_query = query.replace("\\", "\\\\").replace("'", "\\'")
                q_parts.append(f"name contains '{sanitized_query}'")
            q = " and ".join(q_parts)

            params = {
                "q": q,
                "pageSize": max_results,
                "fields": "nextPageToken, files(id, name, mimeType, size, modifiedTime, owners)",
                "orderBy": "folder, name",
            }
            if page_token:
                params["pageToken"] = page_token

            result = self._retry(lambda: self._service.files().list(**params).execute())
            files = [self._parse_file(f) for f in result.get("files", [])]
            next_token = result.get("nextPageToken")
            return files, next_token

        return self._cached(cache_key, ttl=TTL_FILE_LIST, fetch=fetch)

    def list_recent(self, max_results: int = 50) -> list[DriveFile]:
        cache_key = f"{CACHE_PREFIX}recent"

        def fetch():
            result = self._retry(
                lambda: (
                    self._service.files()
                    .list(
                        pageSize=max_results,
                        fields="files(id, name, mimeType, size, modifiedTime, owners)",
                        orderBy="modifiedTime desc",
                        q="trashed = false",
                    )
                    .execute()
                )
            )
            return [self._parse_file(f) for f in result.get("files", [])]

        return self._cached(cache_key, ttl=TTL_FILE_LIST, fetch=fetch)

    def list_shared(self, max_results: int = 50) -> list[DriveFile]:
        cache_key = f"{CACHE_PREFIX}shared"

        def fetch():
            result = self._retry(
                lambda: (
                    self._service.files()
                    .list(
                        pageSize=max_results,
                        fields="files(id, name, mimeType, size, modifiedTime, owners)",
                        orderBy="modifiedTime desc",
                        q="sharedWithMe = true and trashed = false",
                    )
                    .execute()
                )
            )
            return [self._parse_file(f) for f in result.get("files", [])]

        return self._cached(cache_key, ttl=TTL_FILE_LIST, fetch=fetch)

    def get_file_metadata(self, file_id: str) -> DriveFile:
        cache_key = f"{CACHE_PREFIX}meta:{file_id}"

        def fetch():
            result = self._retry(
                lambda: (
                    self._service.files()
                    .get(
                        fileId=file_id,
                        fields="id, name, mimeType, size, modifiedTime, owners",
                    )
                    .execute()
                )
            )
            return self._parse_file(result)

        return self._cached(cache_key, ttl=TTL_FILE_DETAIL, fetch=fetch)

    def download_file(self, file_id: str, dest_dir: Path, filename: str) -> Path:
        metadata = self.get_file_metadata(file_id)
        safe_name = Path(filename).name
        dest_path = dest_dir / safe_name

        if metadata.mime_type in EXPORT_FORMATS:
            export_mime, ext = EXPORT_FORMATS[metadata.mime_type]
            if not dest_path.suffix:
                dest_path = dest_path.with_suffix(ext)
            content = self._retry(
                lambda: self._service.files().export(fileId=file_id, mimeType=export_mime).execute()
            )
            dest_path.write_bytes(content)
        else:
            content = self._retry(lambda: self._service.files().get_media(fileId=file_id).execute())
            dest_path.write_bytes(content)

        logger.info("File downloaded to {}", dest_path)
        return dest_path

    def upload_file(self, local_path: Path, folder_id: str = "root") -> str:
        import mimetypes

        mime_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
        file_metadata: dict = {
            "name": local_path.name,
            "parents": [folder_id],
        }
        media = MediaFileUpload(str(local_path), mimetype=mime_type)
        result = self._retry(
            lambda: (
                self._service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
        )
        self._cache.invalidate_prefix(CACHE_PREFIX)
        logger.info("File uploaded: {}", local_path.name)
        return result["id"]

    def _parse_file(self, data: dict) -> DriveFile:
        mime = data.get("mimeType", "")
        is_folder = mime == "application/vnd.google-apps.folder"

        icon = "📄"
        for mime_prefix, icon_char in MIME_ICONS.items():
            if mime.startswith(mime_prefix):
                icon = icon_char
                break

        owners = data.get("owners", [])
        owner = owners[0].get("emailAddress", "") if owners else ""

        return DriveFile(
            file_id=data.get("id", ""),
            name=data.get("name", ""),
            mime_type=mime,
            size=int(data.get("size", 0)),
            modified_time=data.get("modifiedTime", ""),
            owner=owner,
            is_folder=is_folder,
            icon=icon,
        )
