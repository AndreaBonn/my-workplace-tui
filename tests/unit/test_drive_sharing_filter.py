from workspace_tui.services.drive import DriveFile
from workspace_tui.ui.tabs.drive_tab import DriveTab


def _make_file(owner: str) -> DriveFile:
    return DriveFile(
        file_id="f1",
        name="test.txt",
        mime_type="text/plain",
        owner=owner,
    )


def _make_tab(domain: str = "azienda.com") -> DriveTab:
    tab = DriveTab.__new__(DriveTab)
    tab._workspace_domain = domain
    return tab


class TestFilterBySharing:
    def test_internal_keeps_same_domain(self):
        tab = _make_tab("azienda.com")
        files = [
            _make_file("alice@azienda.com"),
            _make_file("bob@esterno.com"),
            _make_file("carol@azienda.com"),
        ]
        result = tab._filter_by_sharing(files, sharing="interno")
        assert len(result) == 2
        assert all(f.owner.endswith("@azienda.com") for f in result)

    def test_external_keeps_other_domain(self):
        tab = _make_tab("azienda.com")
        files = [
            _make_file("alice@azienda.com"),
            _make_file("bob@esterno.com"),
        ]
        result = tab._filter_by_sharing(files, sharing="esterno")
        assert len(result) == 1
        assert result[0].owner == "bob@esterno.com"

    def test_external_excludes_empty_owner(self):
        tab = _make_tab("azienda.com")
        files = [_make_file(""), _make_file("bob@esterno.com")]
        result = tab._filter_by_sharing(files, sharing="esterno")
        assert len(result) == 1

    def test_unknown_sharing_returns_all(self):
        tab = _make_tab("azienda.com")
        files = [_make_file("alice@azienda.com"), _make_file("bob@esterno.com")]
        result = tab._filter_by_sharing(files, sharing="qualcosa")
        assert len(result) == 2

    def test_internal_empty_list(self):
        tab = _make_tab("azienda.com")
        result = tab._filter_by_sharing([], sharing="interno")
        assert result == []
