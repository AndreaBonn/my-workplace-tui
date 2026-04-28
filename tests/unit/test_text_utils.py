from workspace_tui.utils.text_utils import (
    _extract_adf_text,
    adf_to_text,
    extract_jira_keys,
    format_size,
    html_to_text,
    mime_to_label,
    strip_quoted_text,
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


class TestStripQuotedText:
    def test_empty_input(self):
        assert strip_quoted_text("") == ""

    def test_no_quotes_returns_full_text(self):
        text = "Hello\nThis is original content"
        assert strip_quoted_text(text) == text

    def test_strips_quoted_lines_with_angle_bracket(self):
        text = "Original message\n> Quoted line\n> Another quoted line"
        assert strip_quoted_text(text) == "Original message"

    def test_strips_from_on_wrote_marker(self):
        text = "My reply\nOn Mon, Apr 28, 2026 John wrote:\n> Previous message"
        result = strip_quoted_text(text)
        assert result == "My reply"

    def test_strips_from_original_message_marker(self):
        text = "My reply\n--- Original Message ---\n> Old content"
        result = strip_quoted_text(text)
        assert result == "My reply"

    def test_italian_marker(self):
        text = "Risposta\nIl giorno 28 Apr 2026 Mario ha scritto:\n> Testo precedente"
        result = strip_quoted_text(text)
        assert result == "Risposta"

    def test_keeps_text_when_marker_not_followed_by_quotes(self):
        text = "Line 1\nOn Mon, Apr 28 John wrote:\nStill original content"
        result = strip_quoted_text(text)
        assert "Line 1" in result
        assert "Still original content" in result


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


class TestMimeToLabel:
    def test_known_mime_type(self):
        assert mime_to_label("application/pdf") == "PDF"

    def test_google_folder(self):
        assert mime_to_label("application/vnd.google-apps.folder") == "Cartella Google"

    def test_unknown_image_type(self):
        assert mime_to_label("image/webp") == "Immagine"

    def test_unknown_video_type(self):
        assert mime_to_label("video/webm") == "Video"

    def test_unknown_audio_type(self):
        assert mime_to_label("audio/ogg") == "Audio"

    def test_unknown_text_type(self):
        assert mime_to_label("text/xml") == "Documento testo"

    def test_completely_unknown_type(self):
        assert mime_to_label("application/octet-stream") == "octet-stream"

    def test_no_slash_in_mime(self):
        assert mime_to_label("unknown") == "unknown"


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
                    "content": [{"type": "text", "text": "Line 1"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Line 2"}],
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

    def test_blockquote(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Quoted text"}],
                        }
                    ],
                }
            ],
        }
        result = adf_to_text(adf)
        assert "> " in result
        assert "Quoted text" in result

    def test_non_dict_node_returns_empty(self):
        assert _extract_adf_text("not a dict") == ""
        assert _extract_adf_text(42) == ""

    def test_code_block(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "codeBlock",
                    "content": [{"type": "text", "text": "print('hello')"}],
                }
            ],
        }
        result = adf_to_text(adf)
        assert "print('hello')" in result
