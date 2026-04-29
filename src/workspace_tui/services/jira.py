from dataclasses import dataclass, field

import requests
from loguru import logger

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.base import BaseService
from workspace_tui.utils.text_utils import adf_to_text

CACHE_PREFIX = "jira:"
TTL_ISSUE_LIST = 120
TTL_ISSUE_DETAIL = 60
TTL_TRANSITIONS = 600
TTL_METADATA = 1800
TTL_WORKLOGS = 60


@dataclass
class JiraIssue:
    key: str
    summary: str
    status: str
    status_category: str
    issue_type: str
    priority: str
    assignee: str
    reporter: str
    sprint: str
    description_text: str
    created: str
    updated: str
    estimate_seconds: int
    logged_seconds: int
    labels: list[str] = field(default_factory=list)
    subtasks: list[dict] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)


@dataclass
class JiraComment:
    comment_id: str
    author: str
    body: str
    created: str
    updated: str


@dataclass
class JiraWorklog:
    worklog_id: str
    author: str
    author_account_id: str
    time_spent: str
    time_spent_seconds: int
    started: str
    comment: str


@dataclass
class JiraTransition:
    transition_id: str
    name: str
    to_status: str


class JiraService(BaseService):
    def __init__(self, session: requests.Session, cache: CacheManager) -> None:
        super().__init__(cache=cache)
        self._session = session
        self._base_url = session.base_url.rstrip("/")  # type: ignore[attr-defined]

    def _api_url(self, path: str) -> str:
        return f"{self._base_url}/rest/api/3/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs) -> dict:
        def do_request():
            url = self._api_url(path)
            resp = self._session.request(method, url, **kwargs)
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

        return self._retry(do_request)

    def get_myself(self) -> dict:
        return self._request("GET", "/myself")

    def list_projects(self) -> list[dict]:
        def fetch():
            return self._request("GET", "/project")

        return self._cached(f"{CACHE_PREFIX}projects", ttl=TTL_METADATA, fetch=fetch)

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
    ) -> tuple[list[JiraIssue], int]:
        """Search issues with JQL, returns (issues, total_count)."""
        cache_key = f"{CACHE_PREFIX}search:{jql}:{start_at}:{max_results}"

        def fetch():
            params = {
                "jql": jql,
                "maxResults": max_results,
                "startAt": start_at,
                "fields": "summary,status,issuetype,priority,assignee,reporter,"
                "sprint,description,created,updated,timeestimate,"
                "timespent,labels,subtasks,issuelinks",
            }
            data = self._request("GET", "/search", params=params)
            issues = [self._parse_issue(item) for item in data.get("issues", [])]
            total = data.get("total", 0)
            return issues, total

        return self._cached(cache_key, ttl=TTL_ISSUE_LIST, fetch=fetch)

    def get_issue(self, issue_key: str) -> JiraIssue:
        cache_key = f"{CACHE_PREFIX}issue:{issue_key}"

        def fetch():
            data = self._request("GET", f"/issue/{issue_key}")
            return self._parse_issue(data)

        return self._cached(cache_key, ttl=TTL_ISSUE_DETAIL, fetch=fetch)

    def get_transitions(self, issue_key: str) -> list[JiraTransition]:
        cache_key = f"{CACHE_PREFIX}transitions:{issue_key}"

        def fetch():
            data = self._request("GET", f"/issue/{issue_key}/transitions")
            return [
                JiraTransition(
                    transition_id=t["id"],
                    name=t["name"],
                    to_status=t.get("to", {}).get("name", ""),
                )
                for t in data.get("transitions", [])
            ]

        return self._cached(cache_key, ttl=TTL_TRANSITIONS, fetch=fetch)

    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        self._request(
            "POST",
            f"/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )
        self._cache.invalidate(f"{CACHE_PREFIX}issue:{issue_key}")
        self._cache.invalidate_prefix(f"{CACHE_PREFIX}search:")
        logger.info("Issue {} transitioned (id={})", issue_key, transition_id)

    def get_worklogs(self, issue_key: str) -> list[JiraWorklog]:
        cache_key = f"{CACHE_PREFIX}worklogs:{issue_key}"

        def fetch():
            data = self._request("GET", f"/issue/{issue_key}/worklog")
            return [
                JiraWorklog(
                    worklog_id=w["id"],
                    author=w.get("author", {}).get("displayName", ""),
                    author_account_id=w.get("author", {}).get("accountId", ""),
                    time_spent=w.get("timeSpent", ""),
                    time_spent_seconds=w.get("timeSpentSeconds", 0),
                    started=w.get("started", ""),
                    comment=self._extract_adf_comment(w.get("comment")),
                )
                for w in data.get("worklogs", [])
            ]

        return self._cached(cache_key, ttl=TTL_WORKLOGS, fetch=fetch)

    def add_worklog(
        self,
        issue_key: str,
        time_spent_seconds: int,
        started: str,
        comment: str = "",
    ) -> None:
        body: dict = {
            "timeSpentSeconds": time_spent_seconds,
            "started": started,
        }
        if comment:
            body["comment"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        self._request("POST", f"/issue/{issue_key}/worklog", json=body)
        self._cache.invalidate(f"{CACHE_PREFIX}worklogs:{issue_key}")
        self._cache.invalidate(f"{CACHE_PREFIX}issue:{issue_key}")
        logger.info("Worklog added to {}", issue_key)

    def add_comment(self, issue_key: str, body_text: str) -> None:
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body_text}],
                    }
                ],
            }
        }
        self._request("POST", f"/issue/{issue_key}/comment", json=body)
        self._cache.invalidate(f"{CACHE_PREFIX}issue:{issue_key}")
        logger.info("Comment added to {}", issue_key)

    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        priority: str = "Medium",
        assignee_id: str = "",
        description: str = "",
    ) -> str:
        fields: dict = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
        if assignee_id:
            fields["assignee"] = {"accountId": assignee_id}
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

        result = self._request("POST", "/issue", json={"fields": fields})
        self._cache.invalidate_prefix(f"{CACHE_PREFIX}search:")
        logger.info("Issue created: {}", result.get("key"))
        return result.get("key", "")

    def update_issue(self, issue_key: str, **field_updates) -> None:
        fields: dict = {}
        if "summary" in field_updates:
            fields["summary"] = field_updates["summary"]
        if "priority" in field_updates:
            fields["priority"] = {"name": field_updates["priority"]}
        if "assignee_id" in field_updates:
            fields["assignee"] = {"accountId": field_updates["assignee_id"]}

        self._request("PUT", f"/issue/{issue_key}", json={"fields": fields})
        self._cache.invalidate(f"{CACHE_PREFIX}issue:{issue_key}")
        self._cache.invalidate_prefix(f"{CACHE_PREFIX}search:")
        logger.info("Issue {} updated", issue_key)

    def get_priorities(self) -> list[dict]:
        def fetch():
            return self._request("GET", "/priority")

        return self._cached(f"{CACHE_PREFIX}priorities", ttl=TTL_METADATA, fetch=fetch)

    def get_issue_types(self) -> list[dict]:
        def fetch():
            return self._request("GET", "/issuetype")

        return self._cached(f"{CACHE_PREFIX}issuetypes", ttl=TTL_METADATA, fetch=fetch)

    def search_users(self, query: str) -> list[dict]:
        return self._request("GET", "/user/search", params={"query": query})

    def _parse_issue(self, data: dict) -> JiraIssue:
        fields = data.get("fields", {})
        status = fields.get("status", {})
        assignee = fields.get("assignee") or {}
        reporter = fields.get("reporter") or {}
        sprint_data = fields.get("sprint") or {}
        description = fields.get("description")

        subtasks = [
            {
                "key": st["key"],
                "summary": st["fields"]["summary"],
                "status": st["fields"]["status"]["name"],
            }
            for st in fields.get("subtasks", [])
        ]

        links = [
            {
                "type": link.get("type", {}).get("name", ""),
                "direction": "inward" if "inwardIssue" in link else "outward",
                "issue_key": (link.get("inwardIssue") or link.get("outwardIssue", {})).get(
                    "key", ""
                ),
                "summary": (link.get("inwardIssue") or link.get("outwardIssue", {}))
                .get("fields", {})
                .get("summary", ""),
            }
            for link in fields.get("issuelinks", [])
        ]

        return JiraIssue(
            key=data.get("key", ""),
            summary=fields.get("summary", ""),
            status=status.get("name", ""),
            status_category=status.get("statusCategory", {}).get("name", ""),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            priority=fields.get("priority", {}).get("name", ""),
            assignee=assignee.get("displayName", ""),
            reporter=reporter.get("displayName", ""),
            sprint=sprint_data.get("name", ""),
            description_text=adf_to_text(description) if description else "",
            created=fields.get("created", ""),
            updated=fields.get("updated", ""),
            estimate_seconds=fields.get("timeestimate") or 0,
            logged_seconds=fields.get("timespent") or 0,
            labels=fields.get("labels", []),
            subtasks=subtasks,
            links=links,
        )

    def _extract_adf_comment(self, comment_data: dict | None) -> str:
        if not comment_data:
            return ""
        return adf_to_text(comment_data)
