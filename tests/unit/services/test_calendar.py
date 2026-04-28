from unittest.mock import MagicMock, patch

import pytest

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.calendar import CalendarService


@pytest.fixture
def cache():
    return CacheManager(enabled=False)


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.fixture
def calendar_service(mock_api, cache):
    with patch("workspace_tui.services.calendar.build", return_value=mock_api):
        service = CalendarService(credentials=MagicMock(), cache=cache)
    service._service = mock_api
    return service


class TestListCalendars:
    def test_returns_calendars(self, calendar_service, mock_api):
        mock_api.calendarList().list().execute.return_value = {
            "items": [
                {"id": "primary", "summary": "Mario Rossi", "primary": True},
                {"id": "team@group.calendar.google.com", "summary": "Team"},
            ]
        }
        calendars = calendar_service.list_calendars()
        assert len(calendars) == 2
        assert calendars[0].primary is True


class TestListEvents:
    def test_returns_events(self, calendar_service, mock_api):
        mock_api.events().list().execute.return_value = {
            "items": [
                {
                    "id": "ev1",
                    "summary": "Riunione team",
                    "start": {"dateTime": "2026-04-28T10:00:00+02:00"},
                    "end": {"dateTime": "2026-04-28T11:00:00+02:00"},
                    "location": "Sala A",
                },
            ]
        }
        events = calendar_service.list_events()
        assert len(events) == 1
        assert events[0].summary == "Riunione team"
        assert events[0].location == "Sala A"

    def test_empty_calendar(self, calendar_service, mock_api):
        mock_api.events().list().execute.return_value = {"items": []}
        events = calendar_service.list_events()
        assert events == []

    def test_all_day_event(self, calendar_service, mock_api):
        mock_api.events().list().execute.return_value = {
            "items": [
                {
                    "id": "ev2",
                    "summary": "Ferie",
                    "start": {"date": "2026-04-28"},
                    "end": {"date": "2026-04-29"},
                },
            ]
        }
        events = calendar_service.list_events()
        assert events[0].all_day is True


class TestCreateEvent:
    def test_creates_event(self, calendar_service, mock_api):
        mock_api.events().insert().execute.return_value = {"id": "new_ev"}
        result = calendar_service.create_event(
            summary="Test event",
            start="2026-04-28T10:00:00+02:00",
            end="2026-04-28T11:00:00+02:00",
        )
        assert result == "new_ev"


class TestDeleteEvent:
    def test_deletes_event(self, calendar_service, mock_api):
        mock_api.events().delete().execute.return_value = None
        calendar_service.delete_event("ev1")


class TestParseEvent:
    def test_event_with_meet_link(self, calendar_service):
        data = {
            "id": "ev1",
            "summary": "Call",
            "start": {"dateTime": "2026-04-28T10:00:00"},
            "end": {"dateTime": "2026-04-28T11:00:00"},
            "hangoutLink": "https://meet.google.com/abc-def",
            "attendees": [{"email": "a@test.com"}, {"email": "b@test.com"}],
        }
        event = calendar_service._parse_event(data)
        assert event.meet_link == "https://meet.google.com/abc-def"
        assert len(event.attendees) == 2
