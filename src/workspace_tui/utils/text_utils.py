import re

import html2text

_converter = html2text.HTML2Text()
_converter.ignore_links = False
_converter.ignore_images = True
_converter.body_width = 0
_converter.unicode_snob = True

JIRA_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    return _converter.handle(html_content).strip()


def extract_jira_keys(text: str, project_prefix: str = "") -> list[str]:
    """Extract Jira issue keys from text, optionally filtered by project prefix."""
    keys = JIRA_KEY_PATTERN.findall(text)
    if project_prefix:
        keys = [k for k in keys if k.startswith(f"{project_prefix}-")]
    return list(dict.fromkeys(keys))


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def adf_to_text(adf_document: dict) -> str:
    """Convert Atlassian Document Format (ADF) JSON to plain text."""
    if not adf_document:
        return ""
    return _extract_adf_text(adf_document)


def _extract_adf_text(node: dict) -> str:
    if not isinstance(node, dict):
        return ""

    text_parts: list[str] = []

    if node.get("type") == "text":
        text_parts.append(node.get("text", ""))

    for child in node.get("content", []):
        child_text = _extract_adf_text(child)
        if child_text:
            text_parts.append(child_text)

    node_type = node.get("type", "")
    separator = (
        "\n"
        if node_type
        in (
            "paragraph",
            "heading",
            "bulletList",
            "orderedList",
            "listItem",
            "blockquote",
            "codeBlock",
        )
        else ""
    )

    result = separator.join(text_parts)
    if node_type == "listItem":
        result = f"  - {result}"
    elif node_type == "blockquote":
        result = "\n".join(f"> {line}" for line in result.splitlines())

    return result
