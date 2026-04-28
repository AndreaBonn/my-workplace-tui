from unittest.mock import MagicMock, patch

import pytest

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.drive import DriveService


@pytest.fixture
def cache():
    return CacheManager(enabled=False)


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.fixture
def drive_service(mock_api, cache):
    with patch("workspace_tui.services.drive.build", return_value=mock_api):
        service = DriveService(credentials=MagicMock(), cache=cache)
    service._service = mock_api
    return service


class TestListFiles:
    def test_returns_files(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [
                {
                    "id": "folder1",
                    "name": "Documenti",
                    "mimeType": "application/vnd.google-apps.folder",
                },
                {
                    "id": "file1",
                    "name": "Report.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document",
                    "size": "1048576",
                },
            ]
        }
        files, next_token = drive_service.list_files()
        assert len(files) == 2
        assert files[0].is_folder is True
        assert files[0].icon == "📁"
        assert files[1].size == 1048576
        assert next_token is None


class TestListRecent:
    def test_returns_recent_files(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [{"id": "f1", "name": "Recent.pdf", "mimeType": "application/pdf"}]
        }
        files = drive_service.list_recent()
        assert len(files) == 1


class TestListShared:
    def test_returns_shared_files(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [{"id": "f2", "name": "Shared.xlsx", "mimeType": "application/vnd.ms-excel"}]
        }
        files = drive_service.list_shared()
        assert len(files) == 1


class TestGetFileMetadata:
    def test_returns_metadata(self, drive_service, mock_api):
        mock_api.files().get().execute.return_value = {
            "id": "f1",
            "name": "Test.pdf",
            "mimeType": "application/pdf",
            "size": "2048",
            "modifiedTime": "2026-04-28T14:30:00Z",
            "owners": [{"emailAddress": "owner@test.com"}],
        }
        file = drive_service.get_file_metadata("f1")
        assert file.name == "Test.pdf"
        assert file.size == 2048
        assert file.owner == "owner@test.com"


class TestParseFile:
    def test_google_doc(self, drive_service):
        data = {
            "id": "doc1",
            "name": "My Document",
            "mimeType": "application/vnd.google-apps.document",
        }
        file = drive_service._parse_file(data)
        assert file.icon == "📄"
        assert file.is_folder is False

    def test_google_sheet(self, drive_service):
        data = {
            "id": "sheet1",
            "name": "Budget",
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }
        file = drive_service._parse_file(data)
        assert file.icon == "📊"

    def test_folder(self, drive_service):
        data = {
            "id": "folder1",
            "name": "Projects",
            "mimeType": "application/vnd.google-apps.folder",
        }
        file = drive_service._parse_file(data)
        assert file.is_folder is True
        assert file.icon == "📁"

    def test_no_owners(self, drive_service):
        data = {"id": "f1", "name": "Orphan.txt", "mimeType": "text/plain"}
        file = drive_service._parse_file(data)
        assert file.owner == ""


class TestListSharedDrives:
    def test_returns_shared_drives(self, drive_service, mock_api):
        mock_api.drives().list().execute.return_value = {
            "drives": [
                {"id": "sd1", "name": "Engineering"},
                {"id": "sd2", "name": "Marketing"},
            ]
        }
        drives = drive_service.list_shared_drives()
        assert len(drives) == 2
        assert drives[0].drive_id == "sd1"
        assert drives[0].name == "Engineering"
        assert drives[1].drive_id == "sd2"
        assert drives[1].name == "Marketing"

    def test_returns_empty_when_no_shared_drives(self, drive_service, mock_api):
        mock_api.drives().list().execute.return_value = {"drives": []}
        drives = drive_service.list_shared_drives()
        assert drives == []

    def test_returns_empty_when_no_drives_key(self, drive_service, mock_api):
        mock_api.drives().list().execute.return_value = {}
        drives = drive_service.list_shared_drives()
        assert drives == []


class TestListFilesWithOptions:
    def test_list_files_with_query(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [{"id": "f1", "name": "Found.txt", "mimeType": "text/plain"}]
        }
        files, _ = drive_service.list_files(query="Found")
        assert len(files) == 1

    def test_list_files_with_page_token(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [{"id": "f2", "name": "Page2.txt", "mimeType": "text/plain"}],
            "nextPageToken": "next123",
        }
        files, next_token = drive_service.list_files(page_token="token1")
        assert len(files) == 1
        assert next_token == "next123"


class TestDownloadFile:
    def test_downloads_regular_file(self, drive_service, mock_api, tmp_path):
        mock_api.files().get().execute.return_value = {
            "id": "f1",
            "name": "report.pdf",
            "mimeType": "application/pdf",
        }
        mock_api.files().get_media().execute.return_value = b"PDF content"
        path = drive_service.download_file(file_id="f1", dest_dir=tmp_path, filename="report.pdf")
        assert path.exists()
        assert path.read_bytes() == b"PDF content"

    def test_downloads_google_doc_as_txt(self, drive_service, mock_api, tmp_path):
        mock_api.files().get().execute.return_value = {
            "id": "doc1",
            "name": "My Doc",
            "mimeType": "application/vnd.google-apps.document",
        }
        mock_api.files().export().execute.return_value = b"Plain text content"
        path = drive_service.download_file(file_id="doc1", dest_dir=tmp_path, filename="mydoc")
        assert path.suffix == ".txt"
        assert path.read_bytes() == b"Plain text content"


class TestUploadFile:
    def test_uploads_file(self, drive_service, mock_api, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        mock_api.files().create().execute.return_value = {"id": "uploaded1"}
        result = drive_service.upload_file(local_path=test_file, folder_id="root")
        assert result == "uploaded1"


class TestSearchFiles:
    def test_search_by_name(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [{"id": "f1", "name": "Report Q1.pdf", "mimeType": "application/pdf"}]
        }
        files = drive_service.search_files(name="Report")
        assert len(files) == 1
        assert files[0].name == "Report Q1.pdf"

    def test_search_by_type(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [{"id": "f1", "name": "Budget.xlsx", "mimeType": "application/vnd.ms-excel"}]
        }
        files = drive_service.search_files(file_type="fogli")
        assert len(files) == 1

    def test_search_shared_with_me(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {"files": []}
        files = drive_service.search_files(shared_with_me=True)
        assert files == []

    def test_search_no_filters_returns_all(self, drive_service, mock_api):
        mock_api.files().list().execute.return_value = {
            "files": [
                {"id": "f1", "name": "A.txt", "mimeType": "text/plain"},
                {"id": "f2", "name": "B.txt", "mimeType": "text/plain"},
            ]
        }
        files = drive_service.search_files()
        assert len(files) == 2
