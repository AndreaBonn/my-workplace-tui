from __future__ import annotations

import enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from loguru import logger


class SearchSource(enum.Enum):
    GMAIL = "gmail"
    JIRA = "jira"
    DRIVE = "drive"
    CHAT = "chat"


SOURCE_ICONS: dict[SearchSource, str] = {
    SearchSource.GMAIL: "📧",
    SearchSource.JIRA: "🎫",
    SearchSource.DRIVE: "📁",
    SearchSource.CHAT: "💬",
}

SOURCE_LABELS: dict[SearchSource, str] = {
    SearchSource.GMAIL: "Gmail",
    SearchSource.JIRA: "Jira",
    SearchSource.DRIVE: "Drive",
    SearchSource.CHAT: "Chat",
}

PROVIDER_TIMEOUT = 10
MAX_RESULTS_PER_SOURCE = 10


@dataclass
class SearchResult:
    source: SearchSource
    title: str
    snippet: str
    identifier: str
    url: str
    timestamp: str


@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult]
    errors: dict[SearchSource, str]


class SearchService:
    """Orchestrates parallel search across all workspace services."""

    def __init__(
        self,
        gmail_service=None,
        jira_service=None,
        drive_service=None,
        chat_service=None,
    ) -> None:
        self._gmail = gmail_service
        self._jira = jira_service
        self._drive = drive_service
        self._chat = chat_service

    def search(self, query: str) -> SearchResponse:
        """Fan-out search to all available providers in parallel.

        Parameters
        ----------
        query : str
            The search term. Must be at least 2 characters.

        Returns
        -------
        SearchResponse
            Aggregated results from all providers, plus per-provider errors.
        """
        if len(query.strip()) < 2:
            return SearchResponse(query=query, results=[], errors={})

        providers: dict[SearchSource, callable] = {}
        if self._gmail:
            providers[SearchSource.GMAIL] = lambda: self._search_gmail(query)
        if self._jira:
            providers[SearchSource.JIRA] = lambda: self._search_jira(query)
        if self._drive:
            providers[SearchSource.DRIVE] = lambda: self._search_drive(query)
        if self._chat:
            providers[SearchSource.CHAT] = lambda: self._search_chat(query)

        all_results: list[SearchResult] = []
        errors: dict[SearchSource, str] = {}

        with ThreadPoolExecutor(max_workers=len(providers) or 1) as pool:
            future_to_source = {pool.submit(fn): source for source, fn in providers.items()}
            try:
                for future in as_completed(future_to_source, timeout=PROVIDER_TIMEOUT):
                    source = future_to_source[future]
                    try:
                        results = future.result()
                        all_results.extend(results)
                    except Exception as exc:
                        logger.warning("Search failed for {}: {}", source.value, exc)
                        errors[source] = str(exc)
            except TimeoutError:
                for future, source in future_to_source.items():
                    if not future.done():
                        future.cancel()
                        errors[source] = "Timeout"
                        logger.warning("Search timeout for {}", source.value)

        return SearchResponse(query=query, results=all_results, errors=errors)

    def _search_gmail(self, query: str) -> list[SearchResult]:
        messages, _ = self._gmail.list_messages(
            label_id="",
            max_results=MAX_RESULTS_PER_SOURCE,
            query=query,
        )
        results = []
        for msg in messages:
            results.append(
                SearchResult(
                    source=SearchSource.GMAIL,
                    title=msg.header.subject or "(senza oggetto)",
                    snippet=f"{msg.header.from_address}: {msg.snippet}",
                    identifier=msg.message_id,
                    url=f"https://mail.google.com/mail/#all/{msg.thread_id}",
                    timestamp=msg.header.date,
                )
            )
        return results

    def _search_jira(self, query: str) -> list[SearchResult]:
        safe_query = query.replace('"', '\\"')
        jql = f'text ~ "{safe_query}" ORDER BY updated DESC'
        issues, _ = self._jira.search_issues(
            jql=jql,
            max_results=MAX_RESULTS_PER_SOURCE,
        )
        results = []
        for issue in issues:
            results.append(
                SearchResult(
                    source=SearchSource.JIRA,
                    title=f"{issue.key}: {issue.summary}",
                    snippet=f"[{issue.status}] {issue.assignee} — {issue.issue_type}",
                    identifier=issue.key,
                    url="",
                    timestamp=issue.updated,
                )
            )
        return results

    def _search_drive(self, query: str) -> list[SearchResult]:
        files = self._drive.search_files(
            name=query,
            max_results=MAX_RESULTS_PER_SOURCE,
        )
        results = []
        for f in files:
            results.append(
                SearchResult(
                    source=SearchSource.DRIVE,
                    title=f"{f.icon} {f.name}",
                    snippet=f"{f.owner} — {f.modified_time[:10] if f.modified_time else ''}",
                    identifier=f.file_id,
                    url=f"https://drive.google.com/file/d/{f.file_id}",
                    timestamp=f.modified_time,
                )
            )
        return results

    def _search_chat(self, query: str) -> list[SearchResult]:
        query_lower = query.lower()
        spaces = self._chat.list_spaces()
        results: list[SearchResult] = []

        for space in spaces[:20]:
            try:
                messages = self._chat.list_messages(
                    space_name=space.name,
                    max_results=25,
                )
            except Exception:
                continue

            for msg in messages:
                if query_lower in msg.text.lower():
                    results.append(
                        SearchResult(
                            source=SearchSource.CHAT,
                            title=f"{space.display_name}",
                            snippet=f"{msg.sender_display_name}: {msg.text[:120]}",
                            identifier=msg.name,
                            url="",
                            timestamp=msg.create_time,
                        )
                    )
                    if len(results) >= MAX_RESULTS_PER_SOURCE:
                        return results

        return results
