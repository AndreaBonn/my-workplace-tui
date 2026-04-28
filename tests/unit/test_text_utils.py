from workspace_tui.utils.text_utils import (
    adf_to_text,
    extract_jira_keys,
    format_size,
    html_to_text,
    truncate,
)


class TestHtmlToText:
    def test_simple_html(self):
        result = html_to_text("<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "world" in result

    def test_empty_input(self):
        assert html_to_text("") == ""

    def test_preserves_links(self):
        result = html_to_text('<a href="https://example.com">click</a>')
        assert "example.com" in result

    def test_strips_images(self):
        result = html_to_text('<img src="photo.jpg" alt="photo">')
        assert "photo.jpg" not in result


class TestExtractJiraKeys:
    def test_finds_keys(self):
        text = "Fixed PROJ-142 and related to DATA-55"
        assert extract_jira_keys(text) == ["PROJ-142", "DATA-55"]

    def test_filters_by_project(self):
        text = "Fixed PROJ-142 and DATA-55"
        assert extract_jira_keys(text, project_prefix="PROJ") == ["PROJ-142"]

    def test_no_keys(self):
        assert extract_jira_keys("no issues here") == []

    def test_deduplicates(self):
        text = "PROJ-1 and PROJ-1 again"
        assert extract_jira_keys(text) == ["PROJ-1"]

    def test_ignores_lowercase(self):
        assert extract_jira_keys("proj-123") == []


class TestTruncate:
    def test_short_text_unchanged(self):
        assert truncate("hello", max_length=10) == "hello"

    def test_truncates_with_suffix(self):
        assert truncate("hello world", max_length=8) == "hello..."

    def test_exact_length(self):
        assert truncate("hello", max_length=5) == "hello"

    def test_custom_suffix(self):
        assert truncate("hello world", max_length=8, suffix="~") == "hello w~"


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert format_size(2_500_000) == "2.4 MB"

    def test_gigabytes(self):
        assert format_size(1_500_000_000) == "1.4 GB"

    def test_zero(self):
        assert format_size(0) == "0 B"


class TestAdfToText:
    def test_empty_document(self):
        assert adf_to_text({}) == ""
        assert adf_to_text(None) == ""

    def test_simple_paragraph(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello world"}],
                }
            ],
        }
        assert "Hello world" in adf_to_text(adf)

    def test_nested_content(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Line 1"},
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Line 2"},
                    ],
                },
            ],
        }
        result = adf_to_text(adf)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_list_items(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item 1"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = adf_to_text(adf)
        assert "Item 1" in result
