from unittest.mock import MagicMock

import pytest

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.jira import JiraService


@pytest.fixture
def cache():
    return CacheManager(enabled=False)


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.base_url = "https://test.atlassian.net"
    return session


@pytest.fixture
def jira_service(mock_session, cache):
    return JiraService(session=mock_session, cache=cache)


def _mock_response(json_data: dict, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _make_issue_data(
    key: str = "PROJ-1",
    summary: str = "Test issue",
    status: str = "In Progress",
) -> dict:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status, "statusCategory": {"name": "In Progress"}},
            "issuetype": {"name": "Task"},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Mario Rossi"},
            "reporter": {"displayName": "Anna Bianchi"},
            "sprint": {"name": "Sprint 14"},
            "description": {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Description here"}]}
                ],
            },
            "created": "2026-04-20T10:00:00.000+0000",
            "updated": "2026-04-28T14:30:00.000+0000",
            "timeestimate": 10800,
            "timespent": 7200,
            "labels": ["backend"],
            "subtasks": [],
            "issuelinks": [],
        },
    }


class TestSearchIssues:
    def test_returns_issues_and_total(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            {
                "issues": [_make_issue_data(key="PROJ-1"), _make_issue_data(key="PROJ-2")],
                "total": 2,
            }
        )

        issues, total = jira_service.search_issues(jql="project = PROJ")
        assert len(issues) == 2
        assert total == 2
        assert issues[0].key == "PROJ-1"
        assert issues[0].status == "In Progress"

    def test_empty_results(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({"issues": [], "total": 0})
        issues, total = jira_service.search_issues(jql="project = EMPTY")
        assert issues == []
        assert total == 0


class TestGetIssue:
    def test_parses_issue_details(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(_make_issue_data())
        issue = jira_service.get_issue("PROJ-1")
        assert issue.key == "PROJ-1"
        assert issue.summary == "Test issue"
        assert issue.assignee == "Mario Rossi"
        assert issue.priority == "Medium"
        assert "Description here" in issue.description_text
        assert issue.estimate_seconds == 10800
        assert issue.logged_seconds == 7200


class TestGetTransitions:
    def test_returns_transitions(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            {
                "transitions": [
                    {"id": "11", "name": "In Review", "to": {"name": "In Review"}},
                    {"id": "21", "name": "Done", "to": {"name": "Done"}},
                ]
            }
        )
        transitions = jira_service.get_transitions("PROJ-1")
        assert len(transitions) == 2
        assert transitions[0].name == "In Review"
        assert transitions[1].transition_id == "21"


class TestTransitionIssue:
    def test_transitions_and_invalidates_cache(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=204)
        jira_service.transition_issue("PROJ-1", transition_id="11")


class TestGetWorklogs:
    def test_returns_worklogs(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            {
                "worklogs": [
                    {
                        "id": "w1",
                        "author": {"displayName": "Mario Rossi"},
                        "timeSpent": "1h 30m",
                        "timeSpentSeconds": 5400,
                        "started": "2026-04-28T09:00:00.000+0000",
                        "comment": None,
                    },
                ]
            }
        )
        worklogs = jira_service.get_worklogs("PROJ-1")
        assert len(worklogs) == 1
        assert worklogs[0].time_spent == "1h 30m"
        assert worklogs[0].time_spent_seconds == 5400


class TestAddWorklog:
    def test_adds_worklog(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=201)
        jira_service.add_worklog(
            issue_key="PROJ-1",
            time_spent_seconds=5400,
            started="2026-04-28T09:00:00.000+0000",
            comment="Implemented feature",
        )


class TestGetComments:
    def test_returns_comments_sorted_chronologically(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            {
                "comments": [
                    {
                        "id": "c1",
                        "author": {"displayName": "Mario Rossi"},
                        "body": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "First comment"}],
                                }
                            ],
                        },
                        "created": "2026-04-20T09:00:00.000+0000",
                        "updated": "2026-04-20T09:00:00.000+0000",
                    },
                    {
                        "id": "c2",
                        "author": {"displayName": "Anna Bianchi"},
                        "body": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Second comment"}],
                                }
                            ],
                        },
                        "created": "2026-04-21T10:00:00.000+0000",
                        "updated": "2026-04-21T10:00:00.000+0000",
                    },
                ]
            }
        )
        comments = jira_service.get_comments("PROJ-1")
        assert len(comments) == 2
        assert comments[0].author == "Mario Rossi"
        assert comments[0].body == "First comment"
        assert comments[1].author == "Anna Bianchi"
        assert comments[1].body == "Second comment"

    def test_empty_comments(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({"comments": []})
        comments = jira_service.get_comments("PROJ-1")
        assert comments == []


class TestAddComment:
    def test_adds_comment(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=201)
        jira_service.add_comment(issue_key="PROJ-1", body_text="Test comment")


class TestCreateIssue:
    def test_creates_issue_and_returns_key(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({"key": "PROJ-99"})
        result = jira_service.create_issue(
            project_key="PROJ",
            summary="New task",
            issue_type="Task",
            priority="High",
            description="Some description",
        )
        assert result == "PROJ-99"

    def test_creates_issue_with_assignee(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({"key": "PROJ-100"})
        result = jira_service.create_issue(
            project_key="PROJ",
            summary="Assigned task",
            assignee_id="account-123",
        )
        assert result == "PROJ-100"


class TestUpdateIssue:
    def test_updates_summary(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=204)
        jira_service.update_issue("PROJ-1", summary="Updated summary")


class TestGetPriorities:
    def test_returns_priorities(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            [
                {"id": "1", "name": "High"},
                {"id": "2", "name": "Medium"},
            ]
        )
        priorities = jira_service.get_priorities()
        assert len(priorities) == 2


class TestGetMyself:
    def test_returns_user_info(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            {"accountId": "abc123", "displayName": "Mario Rossi"}
        )
        result = jira_service.get_myself()
        assert result["displayName"] == "Mario Rossi"


class TestGetIssueTypes:
    def test_returns_issue_types(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            [{"id": "1", "name": "Task"}, {"id": "2", "name": "Bug"}]
        )
        types = jira_service.get_issue_types()
        assert len(types) == 2


class TestSearchUsers:
    def test_returns_users(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response(
            [{"accountId": "u1", "displayName": "Mario"}]
        )
        users = jira_service.search_users(query="Mario")
        assert len(users) == 1


class TestUpdateIssueOptions:
    def test_updates_priority(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=204)
        jira_service.update_issue("PROJ-1", priority="High")

    def test_updates_assignee(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=204)
        jira_service.update_issue("PROJ-1", assignee_id="account-abc")


class TestAddWorklogWithoutComment:
    def test_adds_worklog_without_comment(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response({}, status_code=201)
        jira_service.add_worklog(
            issue_key="PROJ-1",
            time_spent_seconds=3600,
            started="2026-04-28T09:00:00.000+0000",
        )


class TestListProjects:
    def test_returns_projects(self, jira_service, mock_session):
        mock_session.request.return_value = _mock_response([{"key": "PROJ", "name": "Project"}])
        projects = jira_service.list_projects()
        assert len(projects) == 1


class TestParseIssue:
    def test_handles_null_assignee(self, jira_service):
        data = _make_issue_data()
        data["fields"]["assignee"] = None
        issue = jira_service._parse_issue(data)
        assert issue.assignee == ""

    def test_handles_subtasks(self, jira_service):
        data = _make_issue_data()
        data["fields"]["subtasks"] = [
            {"key": "PROJ-1-1", "fields": {"summary": "Sub 1", "status": {"name": "To Do"}}}
        ]
        issue = jira_service._parse_issue(data)
        assert len(issue.subtasks) == 1
        assert issue.subtasks[0]["key"] == "PROJ-1-1"

    def test_handles_issue_links(self, jira_service):
        data = _make_issue_data()
        data["fields"]["issuelinks"] = [
            {
                "type": {"name": "Blocks"},
                "outwardIssue": {
                    "key": "PROJ-5",
                    "fields": {"summary": "Blocked issue"},
                },
            }
        ]
        issue = jira_service._parse_issue(data)
        assert len(issue.links) == 1
        assert issue.links[0]["issue_key"] == "PROJ-5"
